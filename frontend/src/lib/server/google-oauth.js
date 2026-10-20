import { env } from '$env/dynamic/private';
import { generateCodeVerifier, generateCodeChallenge, generateState } from '$lib/utils/pkce.js';

const GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth';
const GOOGLE_SCOPES = ['openid', 'email', 'profile'].join(' ');

// Cookie configuration
const COOKIE_OPTIONS = {
  path: '/',
  httpOnly: true,
  sameSite: 'lax'
};

/**
 * Get secure cookie options based on environment
 * @param {number} maxAge - Cookie max age in seconds
 * @returns {object} Cookie options with secure flag for production
 */
function getCookieOptions(maxAge) {
  return {
    ...COOKIE_OPTIONS,
    secure: env.NODE_ENV === 'production',
    maxAge
  };
}

export function googleAvailable() {
  return Boolean(env.GOOGLE_CLIENT_ID && env.GOOGLE_LOGIN_DOMAIN);
}

export function googleError(code) {
  const messages = {
    access_denied: 'Google sign-in was cancelled. Try again or use email.',
    state_mismatch: 'Your sign-in session expired. Please try again.',
    session_expired: 'Your sign-in session expired. Please try again.',
    invitation_required: 'Use the email on your invitation. Accept it before signing in.',
    account_disabled: 'Your account is disabled. Contact your administrator.',
    password_required: 'Use email and password to sign in with this account.'
  };
  return Object.hasOwn(messages, code)
    ? messages[code]
    : 'Google sign-in is unavailable. Try again or use email.';
}

export function clearOAuthCookies(cookies) {
  for (const name of [
    'oauth_state',
    'oauth_code_verifier',
    'oauth_remember_me',
    'oauth_invitation'
  ]) {
    cookies.delete(name, { path: '/' });
  }
}

/**
 * Generate Google OAuth URL with PKCE parameters
 * @param {import('@sveltejs/kit').Cookies} cookies - SvelteKit cookies
 * @param {boolean} rememberMe - Explicit CRM session persistence choice
 * @returns {Promise<string|null>} Google authorization URL when configured
 */
export async function generateOAuthUrl(cookies, rememberMe, invitation = null) {
  if (!googleAvailable()) return null;
  // Generate PKCE parameters
  const codeVerifier = generateCodeVerifier();
  const codeChallenge = await generateCodeChallenge(codeVerifier);

  // Generate cryptographically random state for CSRF protection
  const state = generateState();

  // Store PKCE verifier and state in secure httpOnly cookies
  // These expire in 10 minutes - should be plenty for OAuth flow
  clearOAuthCookies(cookies);
  const oauthCookieMaxAge = 60 * 10; // 10 minutes

  cookies.set('oauth_code_verifier', codeVerifier, getCookieOptions(oauthCookieMaxAge));
  cookies.set('oauth_state', state, getCookieOptions(oauthCookieMaxAge));
  cookies.set('oauth_remember_me', rememberMe ? '1' : '0', getCookieOptions(oauthCookieMaxAge));

  if (invitation)
    cookies.set(
      'oauth_invitation',
      JSON.stringify({ ...invitation, state }),
      getCookieOptions(oauthCookieMaxAge)
    );

  // Build Google OAuth URL with all required parameters
  const redirect_uri = env.GOOGLE_LOGIN_DOMAIN.replace(/\/$/, '') + '/login';

  const params = new URLSearchParams({
    client_id: env.GOOGLE_CLIENT_ID,
    redirect_uri,
    response_type: 'code',
    scope: GOOGLE_SCOPES,
    state,
    code_challenge: codeChallenge,
    code_challenge_method: 'S256',
    prompt: 'select_account' // Sign-in does not need mailbox access or a Google refresh token.
  });

  if (invitation?.email) params.set('login_hint', invitation.email);

  const google_login_url = `${GOOGLE_AUTH_URL}?${params.toString()}`;

  return google_login_url;
}

// Bind the invitation and explicit agreement choices to this one OAuth attempt.
export function invitationContext(cookies) {
  try {
    const value = JSON.parse(cookies.get('oauth_invitation') || 'null');
    return value && value.state === cookies.get('oauth_state') ? value : null;
  } catch {
    return null;
  }
}
