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
