import { env } from '$env/dynamic/private';

// Claims only control cookie persistence here; the API verifies authorization.
function claims(token) {
  try {
    return JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString());
  } catch {
    return {};
  }
}

function lifetime(payload, fallback) {
  if (payload.remember_me === false) return {};
  const expires = payload.session_expires_at
    ? Math.min(payload.exp, payload.session_expires_at)
    : payload.exp;
  return { maxAge: expires ? Math.max(0, Math.floor(expires - Date.now() / 1000)) : fallback };
}
export function saveSessionTokens(cookies, data) {
  const options = {
    path: '/',
    httpOnly: true,
    sameSite: /** @type {const} */ ('lax'),
    secure: env.NODE_ENV === 'production'
  };
  const access = claims(data.access_token);
  const refresh = data.refresh_token ? claims(data.refresh_token) : access;
  cookies.set('jwt_access', data.access_token, { ...options, ...lifetime(access, 3600) });
  if (data.refresh_token)
    cookies.set('jwt_refresh', data.refresh_token, {
      ...options,
      ...lifetime(refresh, 14 * 86400)
    });
  if (data.current_org)
    cookies.set('org', data.current_org.id, { ...options, ...lifetime(refresh, 14 * 86400) });
}

/** A new sign-in/organization selection must not retain a previous membership. */
export function savePasswordSession(cookies, data) {
  cookies.delete('org', { path: '/' });
  saveSessionTokens(cookies, data);
}

export function passwordError(error, fallback) {
  const body = error?.response?.data;
  if (typeof body?.error === 'string') return body.error;
  for (const key of [
    'password',
    'password_confirm',
    'email',
    'name',
    'organization',
    'timezone',
    'detail',
    'non_field_errors'
  ]) {
    if (Array.isArray(body?.[key])) return body[key].join(' ');
    if (typeof body?.[key] === 'string') return body[key];
  }
  return fallback;
}
