import axios from 'axios';
import { fail, redirect } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import { API_ORIGIN } from '$lib/server/api-origin.js';
import { signedJson } from '$lib/server/proxy-identity.js';
import { normalizeLocale } from '$lib/i18n/messages.js';
import { passwordError } from '$lib/server/password-session.js';

const cookieName = 'crm_password_reset';
const cookiePath = '/login/reset';

export function load({ url, cookies }) {
  const uid = url.searchParams.get('uid');
  const token = url.searchParams.get('token');
  const language = url.searchParams.get('lang');
  if (language === 'en' || language === 'es') {
    cookies.set('crm_language', language, {
      path: '/',
      httpOnly: true,
      sameSite: 'lax',
      secure: env.NODE_ENV === 'production',
      maxAge: 31536000
    });
  }
  if (uid && token && /^[a-zA-Z0-9_-]{1,128}$/.test(uid) && /^[a-zA-Z0-9-]{1,128}$/.test(token)) {
    // Keep the credential out of rendered HTML, page data and outgoing referrers.
    // A GET never consumes it, so mail scanners cannot use up the reset link.
    cookies.set(cookieName, JSON.stringify({ uid, token }), {
      path: cookiePath,
      httpOnly: true,
      secure: env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 1800
    });
    redirect(303, cookiePath);
  }
  return {
    ready: Boolean(cookies.get(cookieName)),
    uiLocale: normalizeLocale(cookies.get('crm_language'))
  };
}

export const actions = {
  default: async ({ request, cookies, getClientAddress }) => {
    const form = await request.formData();
    let credential;
    try {
      credential = JSON.parse(cookies.get(cookieName) || 'null');
    } catch {
      credential = null;
    }
    if (!credential?.uid || !credential?.token)
      return fail(400, { error: 'This reset link is invalid or expired. Request a new one.' });
    try {
      const payload = signedJson(
        '/api/auth/password/reset/confirm/',
        {
          uid: credential.uid,
          token: credential.token,
          password: String(form.get('password') || ''),
          password_confirm: String(form.get('password_confirm') || ''),
          language: normalizeLocale(cookies.get('crm_language'))
        },
        getClientAddress
      );
      await axios.post(`${API_ORIGIN}/api/auth/password/reset/confirm/`, payload.body, {
        headers: payload.headers,
        timeout: 15000
      });
    } catch (error) {
      return fail(error.response?.status === 429 ? 429 : 400, {
        error: passwordError(error, 'Password could not be updated. Please try again.')
      });
    }
    cookies.delete(cookieName, { path: cookiePath });
    for (const name of ['jwt_access', 'jwt_refresh', 'org']) cookies.delete(name, { path: '/' });
    return { success: true };
  }
};
