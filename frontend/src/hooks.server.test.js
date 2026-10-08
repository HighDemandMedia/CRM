import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
vi.mock('axios', () => ({ default: { post: vi.fn() } }));
vi.mock('$env/dynamic/private', () => ({ env: { NODE_ENV: 'production' } }));
vi.mock('$lib/server/api-origin.js', () => ({ API_ORIGIN: 'https://api.example.com' }));
import axios from 'axios';
import { handle } from './hooks.server.js';

const orgId = '11111111-1111-4111-8111-111111111111';
function access(seconds = 3600) {
  const payload = {
    exp: Math.floor(Date.now() / 1000) + seconds,
    hash_password: 'test-hash',
    user_id: 'test-user',
    org_id: orgId,
    org_name: 'Test Organization',
    role: 'USER'
  };
  return `header.${Buffer.from(JSON.stringify(payload)).toString('base64url')}.signature`;
}
function input(values, path = '/contacts') {
  const jar = new Map(Object.entries(values));
  const cookies = {
    get: vi.fn((key) => jar.get(key)),
    set: vi.fn((key, value, _options) => jar.set(key, value)),
    delete: vi.fn((key, _options) => jar.delete(key))
  };
  return /** @type {any} */ ({
    event: { cookies, locals: {}, url: new URL(`https://crm.example.com${path}`) },
    resolve: vi.fn(async () => new Response('page'))
  });
}
beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => vi.restoreAllMocks());

describe('persistent session refresh', () => {
  it.each([undefined, 'expired'])('restores access when the access cookie is %s', async (value) => {
    const next = access();
    vi.mocked(axios.post).mockResolvedValue({ data: { access: next, refresh: 'rotated-refresh' } });
    const request = input({
      ...(value ? { jwt_access: access(-60) } : {}),
      jwt_refresh: 'valid-refresh',
      org: orgId
    });
    await handle(request);
    expect(request.event.locals.user.id).toBe('test-user');
    expect(request.event.locals.org.id).toBe(orgId);
    expect(request.resolve).toHaveBeenCalledOnce();
    expect(axios.post).toHaveBeenCalledWith(
      'https://api.example.com/api/auth/refresh-token/',
      { refresh: 'valid-refresh' },
      expect.anything()
    );
    expect(request.event.cookies.get('jwt_refresh')).toBe('rotated-refresh');
  });
  it('keeps valid access without making a refresh request', async () => {
    const request = input({ jwt_access: access(), jwt_refresh: 'valid-refresh', org: orgId });
    await handle(request);
    expect(axios.post).not.toHaveBeenCalled();
    expect(request.resolve).toHaveBeenCalledOnce();
  });
  it('refuses an expired or revoked refresh and removes authentication cookies', async () => {
    vi.mocked(axios.post).mockRejectedValue({ response: { status: 401 } });
    const request = input({ jwt_refresh: 'expired-refresh', org: orgId });
    await expect(handle(request)).rejects.toMatchObject({ status: 307, location: '/login' });
    expect(request.resolve).not.toHaveBeenCalled();
    for (const key of ['jwt_access', 'jwt_refresh', 'org'])
      expect(request.event.cookies.delete).toHaveBeenCalledWith(key, { path: '/' });
  });
  it('shares a rotating refresh across simultaneous requests', async () => {
    let finish = (_value) => {};
    vi.mocked(axios.post).mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        })
    );
    const first = input({ jwt_refresh: 'shared-refresh', org: orgId });
    const second = input({ jwt_refresh: 'shared-refresh', org: orgId });
    const pending = Promise.all([handle(first), handle(second)]);
    expect(axios.post).toHaveBeenCalledOnce();
    finish({ data: { access: access(), refresh: 'shared-replacement' } });
    await pending;
    expect(first.event.cookies.get('jwt_refresh')).toBe('shared-replacement');
    expect(second.event.cookies.get('jwt_refresh')).toBe('shared-replacement');
  });
  it('allows public pages without a session and rejects protected ones', async () => {
    await handle(input({}, '/login'));
    await expect(handle(input({}))).rejects.toMatchObject({ location: '/login' });
    expect(axios.post).not.toHaveBeenCalled();
  });
});

it('restores the organization from the refreshed session if its cookie also expired', async () => {
  vi.mocked(axios.post).mockResolvedValue({ data: { access: access(), refresh: 'replacement' } });
  const request = input({ jwt_refresh: 'valid-refresh' });
  await handle(request);
  expect(request.event.locals.org.id).toBe(orgId);
  expect(request.event.cookies.set).toHaveBeenCalledWith(
    'org',
    orgId,
    expect.objectContaining({ maxAge: 14 * 86400, httpOnly: true, secure: true })
  );
  expect(axios.post).toHaveBeenCalledOnce();
});

it('does not establish a session from an unusable refresh response', async () => {
  vi.mocked(axios.post).mockResolvedValue({ data: { access: 'invalid', refresh: 'replacement' } });
  const request = input({ jwt_refresh: 'valid-refresh', org: orgId });
  await expect(handle(request)).rejects.toMatchObject({ location: '/login' });
  expect(request.event.cookies.set).not.toHaveBeenCalled();
  expect(request.resolve).not.toHaveBeenCalled();
});
