import { afterEach, describe, expect, it, vi } from 'vitest';
vi.mock('axios', () => ({ default: { post: vi.fn() } }));
vi.mock('$env/dynamic/private', () => ({ env: { NODE_ENV: 'production' } }));
import axios from 'axios';
import { env } from '$env/dynamic/private';
import { actions, load } from './+page.server.js';

afterEach(() => {
  delete env.CRM_PROXY_SIGNING_KEY;
  vi.restoreAllMocks();
});

/** @returns {any} */
function input() {
  const form = new FormData();
  form.set('email', 'test@example.com');
  form.set('password', 'test-password-not-real');
  return {
    request: { formData: async () => form },
    cookies: { set: vi.fn(), delete: vi.fn(), get: vi.fn() }
  };
}

describe('password sign-in action', () => {
  it.each(['', {}, { access_token: 'token' }])(
    'rejects an incomplete session response without setting cookies',
    async (body) => {
      vi.spyOn(console, 'error').mockImplementation(() => {});
      vi.mocked(axios.post).mockResolvedValue({ data: body });
      const event = input();
      const result = /** @type {any} */ (await actions.password(event));
      expect(result.status).toBe(400);
      expect(result.data.error).toBe('Sign-in is unavailable. Please try again.');
      expect(event.cookies.set).not.toHaveBeenCalled();
    }
  );
  it('reports a timeout safely and preserves the email for retry', async () => {
    const log = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.mocked(axios.post).mockRejectedValue({
      message: 'timeout',
      code: 'ECONNABORTED',
      config: { data: { password: 'test-password-not-real' } }
    });
    const result = /** @type {any} */ (await actions.password(input()));
    expect(result.data.email).toBe('test@example.com');
    expect(JSON.stringify(log.mock.calls)).not.toContain('test-password-not-real');
  });
  it('stores a valid session and redirects to the CRM', async () => {
    vi.mocked(axios.post).mockResolvedValue({
      data: {
        access_token: 'access',
        refresh_token: 'refresh',
        current_org: { id: 'org' }
      }
    });
    const event = input();
    await expect(actions.password(event)).rejects.toMatchObject({ status: 303, location: '/' });
    expect(event.cookies.set).toHaveBeenCalledWith(
      'jwt_access',
      'access',
      expect.objectContaining({ httpOnly: true, secure: true })
    );
  });
});

describe('sign-in language', () => {
  function languageEvent(query, initial = {}) {
    const values = new Map(Object.entries(initial));
    return /** @type {any} */ ({
      url: new URL(`https://crm.example.test/login${query}`),
      cookies: {
        get: (name) => values.get(name),
        set: vi.fn((name, value) => values.set(name, value))
      }
    });
  }
  it('keeps the selected language when moving to sign-in', async () => {
    const event = languageEvent('?lang=es');
    expect(await load(event)).toMatchObject({ uiLocale: 'es', recovery: false });
    expect(event.cookies.set).toHaveBeenCalledWith(
      'crm_language',
      'es',
      expect.objectContaining({
        path: '/',
        httpOnly: true,
        secure: true,
        sameSite: 'lax'
      })
    );
    event.url = new URL('https://crm.example.test/login?signin=1');
    expect(await load(event)).toMatchObject({ uiLocale: 'es', recovery: false });
  });
  it('ignores unsupported language input without replacing an existing preference', async () => {
    const event = languageEvent('?lang=fr', { crm_language: 'es' });
    expect(await load(event)).toMatchObject({ uiLocale: 'es' });
    expect(event.cookies.set).not.toHaveBeenCalled();
  });
  it('keeps recovery available from the direct sign-in page', async () => {
    const event = languageEvent('?recover=1&lang=es');
    expect(await load(event)).toMatchObject({ uiLocale: 'es', recovery: true });
  });
  it('continues an accepted invitation for an authenticated user', async () => {
    const event = languageEvent('?lang=en', {
      jwt_access: 'existing-session',
      crm_invitation: 'pending-invitation'
    });
    await expect(load(event)).rejects.toMatchObject({ status: 307, location: '/invite' });
  });
  it('preserves the authenticated-user redirect', async () => {
    const event = languageEvent('?lang=en', { jwt_access: 'existing-session' });
    await expect(load(event)).rejects.toMatchObject({ status: 307, location: '/org' });
  });
});

it.each(['password', 'recovery'])(
  'forwards the adapter identity for %s, not a browser header',
  async (action) => {
    env.CRM_PROXY_SIGNING_KEY = 'ab'.repeat(32);
    const event = input();
    event.getClientAddress = () => '198.51.100.10';
    event.request.headers = new Headers({ 'X-Forwarded-For': '203.0.113.99' });
    vi.mocked(axios.post).mockResolvedValue({
      data: {
        access_token: 'access',
        refresh_token: 'refresh',
        current_org: { id: 'org' }
      }
    });
    if (action === 'password') {
      await expect(actions.password(event)).rejects.toMatchObject({ status: 303 });
    } else {
      expect(await actions.recovery(event)).toMatchObject({ success: true });
    }
    const call = vi.mocked(axios.post).mock.lastCall;
    expect(call?.[2]?.headers).toMatchObject({ 'X-CRM-Client-IP': '198.51.100.10' });
    expect(call?.[2]?.headers).not.toHaveProperty('X-Forwarded-For');
    expect(JSON.parse(String(call?.[1]))).toMatchObject({ email: 'test@example.com' });
  }
);

it.each([false, true])('passes the explicit remember choice to the API: %s', async (remember) => {
  const event = input();
  const form = await event.request.formData();
  if (remember) form.set('remember_me', 'on');
  vi.spyOn(console, 'error').mockImplementation(() => {});
  vi.mocked(axios.post).mockRejectedValue({ response: { status: 401 } });
  const result = await actions.password(event);
  const encoded = vi.mocked(axios.post).mock.lastCall[1];
  if (typeof encoded !== 'string') throw new Error('Expected signed JSON body');
  const body = JSON.parse(encoded);
  expect(body.remember_me).toBe(remember);
  expect(result).toMatchObject({ data: { remember_me: remember } });
});

it('requests a password reset instead of a magic login link', async () => {
  const event = input();
  event.cookies.get.mockReturnValue('es');
  vi.mocked(axios.post).mockResolvedValue({ data: { message: 'Accepted' } });
  await actions.recovery(event);
  const [url, body] = vi.mocked(axios.post).mock.lastCall;
  expect(url).toContain('/api/auth/password/reset/request/');
  if (typeof body !== 'string') throw new Error('Expected signed JSON body');
  expect(JSON.parse(body)).toEqual({ email: 'test@example.com', language: 'es' });
});

describe('primary Google sign-in', () => {
  function event(query = '', saved = {}) {
    const values = new Map(Object.entries(saved));
    return /** @type {any} */ ({
      url: new URL(`https://crm.example.test/login${query}`),
      request: { formData: async () => new FormData() },
      getClientAddress: () => '198.51.100.10',
      cookies: {
        get: (name) => values.get(name),
        set: vi.fn((name, value) => values.set(name, value)),
        delete: vi.fn((name) => values.delete(name))
      }
    });
  }

  afterEach(() => {
    delete env.GOOGLE_CLIENT_ID;
    delete env.GOOGLE_LOGIN_DOMAIN;
  });
  function configure() {
    env.GOOGLE_CLIENT_ID = 'test-client';
    env.GOOGLE_LOGIN_DOMAIN = 'https://crm.example.test/';
  }

  it('keeps password available without Google configuration', async () => {
    expect(await load(event())).toMatchObject({ google_available: false });
    expect(await actions.google(event())).toMatchObject({ status: 503 });
  });
  it('offers Google first and opens email only when requested', async () => {
    configure();
    const e = event();
    expect(await load(e)).toMatchObject({ google_available: true, password: false });
    expect(e.cookies.set).not.toHaveBeenCalled(); // Loading/reloading cannot invalidate another tab's OAuth.
    expect(await load(event('?method=password'))).toMatchObject({ password: true });
  });
  it.each([false, true])(
    'starts PKCE only on submission and remembers choice %s',
    async (remember) => {
      configure();
      const e = event();
      e.request.formData = async () => new URLSearchParams(remember ? 'remember_me=on' : '');
      let destination;
      try {
        await actions.google(e);
      } catch (error) {
        destination = error.location;
      }
      const url = new URL(destination);
      expect(url.origin).toBe('https://accounts.google.com');
      expect(url.searchParams.get('scope')).toBe('openid email profile');
      expect(url.searchParams.get('redirect_uri')).toBe('https://crm.example.test/login');
      expect(url.searchParams.get('prompt')).toBe('select_account');
      expect(url.searchParams.has('access_type')).toBe(false);
      expect(url.searchParams.get('code_challenge_method')).toBe('S256');
      expect(url.searchParams.get('state')).toBe(e.cookies.get('oauth_state'));
      expect(e.cookies.get('oauth_remember_me')).toBe(remember ? '1' : '0');
      expect(e.cookies.set).toHaveBeenCalledWith(
        'oauth_state',
        expect.any(String),
        expect.objectContaining({ httpOnly: true, secure: true, sameSite: 'lax', maxAge: 600 })
      );
    }
  );
  it('allows another attempt after cancellation without echoing provider input', async () => {
    configure();
    const e = event('?error=access_denied&error_description=secret', { oauth_state: 'old' });
    expect(await load(e)).toMatchObject({
      google_available: true,
      error: 'Google sign-in was cancelled. Try again or use email.'
    });
    expect(e.cookies.get('oauth_state')).toBeUndefined();
  });
  it.each([
    {},
    { oauth_state: 'wrong', oauth_code_verifier: 'verifier' },
    { oauth_state: 'state' }
  ])('rejects callbacks without matching one-use state and verifier', async (saved) => {
    configure();
    vi.mocked(axios.post).mockClear();
    await expect(load(event('?code=code&state=state', saved))).rejects.toMatchObject({
      status: 303
    });
    expect(axios.post).not.toHaveBeenCalled();
  });
  it('sends signed visitor context, preserves invitation, and prevents callback replay', async () => {
    configure();
    env.CRM_PROXY_SIGNING_KEY = 'ab'.repeat(32);
    const e = event('?code=code&state=state', {
      oauth_state: 'state',
      oauth_code_verifier: 'verifier',
      oauth_remember_me: '1',
      crm_invitation: 'pending'
    });
    vi.mocked(axios.post).mockResolvedValue({
      data: { access_token: 'access', refresh_token: 'refresh' }
    });
    await expect(load(e)).rejects.toMatchObject({ status: 303, location: '/invite' });
    const [url, body, options] = vi.mocked(axios.post).mock.lastCall;
    expect(url).toContain('/api/auth/google/callback/');
    expect(JSON.parse(String(body))).toMatchObject({
      code: 'code',
      code_verifier: 'verifier',
      remember_me: true
    });
    expect(options.headers['X-CRM-Client-IP']).toBe('198.51.100.10');
    expect(e.cookies.get('org')).toBeUndefined();
    vi.mocked(axios.post).mockClear();
    await expect(load(e)).rejects.toMatchObject({ location: '/login?error=state_mismatch' });
    expect(axios.post).not.toHaveBeenCalled();
  });
  it.each(['invitation_required', 'account_disabled', 'password_required', 'raw provider message'])(
    'classifies API failures safely: %s',
    async (code) => {
      configure();
      vi.spyOn(console, 'error').mockImplementation(() => {});
      vi.mocked(axios.post).mockRejectedValue({ response: { status: 403, data: { code } } });
      const e = event('?code=code&state=state', {
        oauth_state: 'state',
        oauth_code_verifier: 'verifier'
      });
      await expect(load(e)).rejects.toMatchObject({
        location: `/login?error=${code === 'raw provider message' ? 'auth_failed' : code}`
      });
      expect(e.cookies.set).not.toHaveBeenCalled();
    }
  );
  it('rejects incomplete session tokens', async () => {
    configure();
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.mocked(axios.post).mockResolvedValue({ data: { access_token: 'access' } });
    const e = event('?code=code&state=state', {
      oauth_state: 'state',
      oauth_code_verifier: 'verifier'
    });
    await expect(load(e)).rejects.toMatchObject({ location: '/login?error=auth_failed' });
    expect(e.cookies.set).not.toHaveBeenCalled();
  });
});
