import { signedJson } from '$lib/server/proxy-identity.js';
import { normalizeLocale } from '$lib/i18n/messages.js';
import { API_ORIGIN } from '$lib/server/api-origin.js';
import { savePasswordSession, passwordError } from '$lib/server/password-session.js';
/**
 * Login Page - Secure OAuth Implementation
 *
 * Security features:
 * - PKCE (Proof Key for Code Exchange) for authorization code protection
 * - Cryptographic state parameter for CSRF protection
 * - Server-side token exchange via Django backend (no client secret in frontend)
 * - Secure httpOnly cookies for sensitive data
 *
 * Django endpoint: POST /api/auth/google/callback/
 */

import axios from 'axios';
import { redirect, fail } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import {
  googleAvailable,
  googleError,
  clearOAuthCookies,
  generateOAuthUrl,
  invitationContext
} from '$lib/server/google-oauth.js';
import { describeError } from '$lib/server/log-safe.js';

/** @type {import('@sveltejs/kit').ServerLoad} */
export async function load({ url, cookies, getClientAddress }) {
  const language = url.searchParams.get('lang');
  if (language === 'en' || language === 'es') {
    cookies.set('crm_language', language, {
      path: '/',
      httpOnly: true,
      sameSite: 'lax',
      secure: url.protocol === 'https:',
      maxAge: 31536000
    });
  }
  const uiLocale = normalizeLocale(cookies.get('crm_language'));
  const code = url.searchParams.get('code');
  const returnedState = url.searchParams.get('state');
  const error = url.searchParams.get('error');
  // Provider errors are untrusted input; show only our own concise messages.
  if (error) {
    const joining = Boolean(invitationContext(cookies));
    clearOAuthCookies(cookies);
    if (joining)
      redirect(
        303,
        `/register?error=${error === 'access_denied' ? 'access_denied' : 'auth_failed'}`
      );
    return {
      uiLocale,
      google_available: googleAvailable(),
      error: googleError(error)
    };
  }

  if (code) {
    return handleOAuthCallback(code, returnedState, cookies, getClientAddress);
  }

  // Check if user is already authenticated
  const jwtAccess = cookies.get('jwt_access');
  if (jwtAccess) {
    throw redirect(307, cookies.get('crm_invitation') ? '/invite' : '/org');
  }

  // OAuth starts only when the user submits the Google sign-in form.
  return {
    uiLocale,
    google_available: googleAvailable(),
    password: url.searchParams.get('method') === 'password',
    recovery: url.searchParams.get('recover') === '1'
  };
}

async function handleOAuthCallback(code, returnedState, cookies, getClientAddress) {
  const savedState = cookies.get('oauth_state');
  const codeVerifier = cookies.get('oauth_code_verifier');
  const rememberMe = cookies.get('oauth_remember_me') === '1';
  const invitation = invitationContext(cookies);
  const hadInvitation = Boolean(cookies.get('oauth_invitation'));
  let joined = false;
  clearOAuthCookies(cookies);

  if (!savedState || savedState !== returnedState) {
    redirect(303, '/login?error=state_mismatch');
  }
  if (hadInvitation && (!invitation || invitation.token !== cookies.get('crm_invitation'))) {
    redirect(303, '/register?error=session_expired');
  }
  if (!codeVerifier || !googleAvailable()) {
    redirect(303, '/login?error=session_expired');
  }

  try {
    const path = '/api/auth/google/callback/';
    const payload = signedJson(
      path,
      {
        code,
        code_verifier: codeVerifier,
        redirect_uri: env.GOOGLE_LOGIN_DOMAIN.replace(/\/$/, '') + '/login',
        remember_me: rememberMe,
        ...(invitation
          ? {
              invitation: invitation.token,
              legal_version: invitation.legal?.legal_version,
              legal_locale: invitation.legal?.legal_locale,
              accept_terms: invitation.legal?.accept_terms === true,
              organization_authority: invitation.legal?.organization_authority === true
            }
          : {})
      },
      getClientAddress
    );
    const response = await axios.post(`${API_ORIGIN}${path}`, payload.body, {
      headers: payload.headers,
      timeout: 30000
    });
    if (
      !response.data ||
      typeof response.data.access_token !== 'string' ||
      !response.data.access_token ||
      typeof response.data.refresh_token !== 'string' ||
      !response.data.refresh_token
    ) {
      throw new Error('Sign-in response did not contain session tokens');
    }
    joined = response.data.invitation_accepted === true && Boolean(response.data.current_org);
    savePasswordSession(cookies, response.data);
  } catch (error) {
    console.error('Google sign-in failed:', describeError(error));
    const code = error.response?.data?.code;
    const knownCode = ['invitation_required', 'account_disabled', 'password_required'].includes(
      code
    );
    redirect(
      303,
      `${invitation ? '/register' : '/login'}?error=${knownCode ? code : 'auth_failed'}`
    );
  }

  if (joined) {
    cookies.delete('crm_invitation', { path: '/' });
    redirect(303, '/onboarding');
  }
  redirect(303, cookies.get('crm_invitation') ? '/invite' : '/org');
}

/** @type {import('@sveltejs/kit').Actions} */
export const actions = {
  google: async ({ request, cookies }) => {
    const form = await request.formData();
    const url = await generateOAuthUrl(cookies, form.get('remember_me') === 'on');
    if (!url) return fail(503, { error: googleError('unavailable') });
    redirect(303, url);
  },
  password: async ({ request, cookies, getClientAddress }) => {
    const form = await request.formData();
    let data;
    try {
      const payload = signedJson(
        '/api/auth/password/login/',
        {
          email: String(form.get('email') || '').trim(),
          password: String(form.get('password') || ''),
          remember_me: form.get('remember_me') === 'on'
        },
        getClientAddress
      );
      const response = await axios.post(`${API_ORIGIN}/api/auth/password/login/`, payload.body, {
        headers: payload.headers,
        timeout: 15000
      });
      data = response.data;
      if (
        !data ||
        typeof data.access_token !== 'string' ||
        !data.access_token ||
        typeof data.refresh_token !== 'string' ||
        !data.refresh_token
      ) {
        throw new Error('Sign-in response did not contain session tokens');
      }
    } catch (error) {
      console.error('Password sign-in failed:', describeError(error));
      return fail(error.response?.status === 429 ? 429 : 400, {
        error: passwordError(error, 'Sign-in is unavailable. Please try again.'),
        email: String(form.get('email') || ''),
        remember_me: form.get('remember_me') === 'on'
      });
    }
    savePasswordSession(cookies, data);
    redirect(303, cookies.get('crm_invitation') ? '/invite' : data.current_org ? '/' : '/org');
  },
  recovery: async ({ request, cookies, getClientAddress }) => {
    const formData = await request.formData();
    const email = formData.get('email');

    if (!email) {
      return fail(400, { error: 'Email is required', recovery: true });
    }

    try {
      const apiUrl = API_ORIGIN;
      const payload = signedJson(
        '/api/auth/password/reset/request/',
        { email, language: normalizeLocale(cookies.get('crm_language')) },
        getClientAddress
      );
      await axios.post(`${apiUrl}/api/auth/password/reset/request/`, payload.body, {
        headers: payload.headers,
        timeout: 10000
      });
      return { success: true, recovery: true, email: String(email) };
    } catch {
      return fail(503, {
        error: 'Email could not be sent. Please try again shortly.',
        recovery: true,
        email: String(email)
      });
    }
  }
};
