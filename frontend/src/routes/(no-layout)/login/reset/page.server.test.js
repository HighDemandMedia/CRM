import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('axios', () => ({ default: { post: vi.fn() } }));
vi.mock('$env/dynamic/private', () => ({ env: { NODE_ENV: 'production' } }));
import axios from 'axios';
import { load, actions } from './+page.server.js';

/** @returns {any} Partial SvelteKit event used by these server-action tests. */
function event(query = '') {
  const values = new Map();
  const fields = new FormData();
  fields.set('password', 'New-test-password-98374!');
  fields.set('password_confirm', 'New-test-password-98374!');
  return {
    url: new URL(`https://crm.example.test/login/reset${query}`),
    cookies: {
      get: (key) => values.get(key),
      set: vi.fn((key, value) => values.set(key, value)),
      delete: vi.fn()
    },
    request: { formData: async () => fields },
    getClientAddress: () => '127.0.0.1'
  };
}
beforeEach(() => vi.clearAllMocks());
it('removes credentials from the URL without consuming them on GET', () => {
  const input = event('?uid=testuid&token=test-token&lang=es');
  expect(() => load(input)).toThrow();
  expect(axios.post).not.toHaveBeenCalled();
  expect(input.cookies.set).toHaveBeenCalledWith(
    'crm_password_reset',
    JSON.stringify({ uid: 'testuid', token: 'test-token' }),
    expect.objectContaining({ httpOnly: true, secure: true, maxAge: 1800 })
  );
  input.url.search = '';
  expect(load(input)).toEqual({ ready: true, uiLocale: 'es' });
});
it('does not call the API without a reset credential', async () => {
  const result = await actions.default(event());
  expect(result).toMatchObject({ status: 400 });
  expect(axios.post).not.toHaveBeenCalled();
});
it('clears local sessions after resetting without automatically signing in', async () => {
  const input = event();
  input.cookies.set('crm_password_reset', JSON.stringify({ uid: 'uid', token: 'test-token' }));
  input.cookies.set.mockClear();
  vi.mocked(axios.post).mockResolvedValue({ data: { message: 'Password updated.' } });
  expect(await actions.default(input)).toEqual({ success: true });
  expect(input.cookies.set).not.toHaveBeenCalled();
  expect(input.cookies.delete).toHaveBeenCalledWith('crm_password_reset', { path: '/login/reset' });
  for (const key of ['jwt_access', 'jwt_refresh', 'org'])
    expect(input.cookies.delete).toHaveBeenCalledWith(key, { path: '/' });
});
it('keeps validation errors recoverable without exposing passwords or tokens', async () => {
  const input = event();
  input.cookies.set('crm_password_reset', JSON.stringify({ uid: 'uid', token: 'private-token' }));
  vi.mocked(axios.post).mockRejectedValue({
    response: { status: 400, data: { password: ['Passwords do not match.'] } },
    config: { data: 'private-token' }
  });
  const result = await actions.default(input);
  expect(result).toMatchObject({ data: { error: 'Passwords do not match.' } });
  expect(input.cookies.delete).not.toHaveBeenCalled();
});
