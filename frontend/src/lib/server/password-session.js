import { env } from '$env/dynamic/private';

// Match the API's one-hour access and fourteen-day rotating refresh lifetimes.
export function saveSessionTokens(cookies, data) {
  const options = {
    path: '/',
    httpOnly: true,
    sameSite: /** @type {const} */ ('lax'),
    secure: env.NODE_ENV === 'production'
  };
  cookies.set('jwt_access', data.access_token, { ...options, maxAge: 3600 });
  if (data.refresh_token)
    cookies.set('jwt_refresh', data.refresh_token, { ...options, maxAge: 14 * 86400 });
  if (data.current_org) cookies.set('org', data.current_org.id, { ...options, maxAge: 14 * 86400 });
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
