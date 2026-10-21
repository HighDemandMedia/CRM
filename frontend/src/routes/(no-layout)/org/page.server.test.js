import { beforeEach, describe, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
vi.mock('$env/dynamic/private', () => ({ env: { NODE_ENV: 'production' } }));
import { apiRequest } from '$lib/api-helpers.js';
import { load } from './+page.server.js';

/** @param {Record<string, string>} [values] @param {any} [locals] */
function input(values = {}, locals = { user: { id: 'user' } }) {
  const jar = new Map(Object.entries({ jwt_access: 'access', jwt_refresh: 'refresh', ...values }));
  return /** @type {any} */ ({
    locals,
    cookies: {
      get: (key) => jar.get(key),
      set: vi.fn((key, value) => jar.set(key, value)),
      delete: vi.fn((key) => jar.delete(key))
    },
    setHeaders: vi.fn()
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

describe('direct organization entry', () => {
  it('requires an authenticated user', async () => {
    await expect(load(input({}, {}))).rejects.toMatchObject({ status: 303, location: '/login' });
    expect(apiRequest).not.toHaveBeenCalled();
  });
  it('continues an invitation before entering an existing workspace', async () => {
    const event = input({ crm_invitation: 'pending' }, { user: {}, org: { id: 'old' } });
    await expect(load(event)).rejects.toMatchObject({ location: '/invite' });
    expect(apiRequest).not.toHaveBeenCalled();
  });
  it('keeps the current workspace without extra API calls or token rotation', async () => {
    const event = input({}, { user: {}, org: { id: 'current' } });
    await expect(load(event)).rejects.toMatchObject({ location: '/' });
    expect(apiRequest).not.toHaveBeenCalled();
    expect(event.cookies.set).not.toHaveBeenCalled();
    expect(event.setHeaders).toHaveBeenCalledWith({ 'Cache-Control': 'private, no-store' });
  });
  it.each(['USER', 'MANAGER', 'ADMIN'])(
    'opens the authorized workspace for %s and preserves the app onboarding gate',
    async (role) => {
      const event = input();
      vi.mocked(apiRequest)
        .mockResolvedValueOnce({ organizations: [{ id: 'allowed', role }, { id: 'other' }] })
        .mockResolvedValueOnce({
          access_token: 'next-access',
          refresh_token: 'next-refresh',
          current_org: { id: 'allowed' }
        });
      await expect(load(event)).rejects.toMatchObject({ status: 303, location: '/' });
      expect(apiRequest).toHaveBeenLastCalledWith(
        '/auth/switch-org/',
        { method: 'POST', body: { org_id: 'allowed', refresh: 'refresh' } },
        { cookies: event.cookies }
      );
      expect(event.cookies.set).toHaveBeenCalledWith('org', 'allowed', expect.any(Object));
    }
  );
  it.each([false, true])('handles no memberships, platform owner: %s', async (owner) => {
    vi.mocked(apiRequest).mockResolvedValue({ organizations: [], is_platform_owner: owner });
    expect(await load(input())).toEqual({ canCreateOrganization: owner });
    expect(apiRequest).toHaveBeenCalledTimes(1);
  });
  it('does not mistake service failure for an empty organization list', async () => {
    vi.mocked(apiRequest).mockRejectedValue({ status: 503 });
    await expect(load(input())).rejects.toMatchObject({ status: 503 });
  });
  it('does not fall through to another workspace when membership is revoked', async () => {
    const event = input();
    vi.mocked(apiRequest)
      .mockResolvedValueOnce({ organizations: [{ id: 'revoked' }, { id: 'other' }] })
      .mockRejectedValueOnce({ status: 403 });
    await expect(load(event)).rejects.toMatchObject({ status: 403 });
    expect(event.cookies.set).not.toHaveBeenCalled();
    expect(apiRequest).toHaveBeenCalledTimes(2);
  });
  it('clears a rejected session instead of redirecting in a sign-in loop', async () => {
    const event = input();
    vi.mocked(apiRequest).mockRejectedValue({ status: 401 });
    await expect(load(event)).rejects.toMatchObject({ location: '/login' });
    for (const key of ['org', 'jwt_access', 'jwt_refresh'])
      expect(event.cookies.delete).toHaveBeenCalledWith(key, { path: '/' });
  });
  it('rejects incomplete session responses without replacing cookies', async () => {
    const event = input();
    vi.mocked(apiRequest)
      .mockResolvedValueOnce({ organizations: [{ id: 'allowed' }] })
      .mockResolvedValueOnce({ access_token: 'incomplete' });
    await expect(load(event)).rejects.toMatchObject({ status: 503 });
    expect(event.cookies.set).not.toHaveBeenCalled();
  });
});
