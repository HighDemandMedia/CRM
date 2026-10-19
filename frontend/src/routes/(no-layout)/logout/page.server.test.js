import { expect, it, vi } from 'vitest';
import { load } from './+page.server.js';

it.each([undefined, 'pending-invitation'])(
  'clears authentication and preserves a pending invitation: %s',
  async (invitation) => {
    const values = {
      jwt_access: 'access',
      jwt_refresh: 'refresh',
      org: 'org',
      crm_invitation: invitation
    };
    const cookies = { get: vi.fn((name) => values[name]), delete: vi.fn() };
    const locals = { user: {}, org: {} };
    const fetch = vi.fn(async () => new Response());
    await expect(load(/** @type {any} */ ({ cookies, locals, fetch }))).rejects.toMatchObject({
      status: 303,
      location: invitation ? '/invite' : '/login'
    });
    expect(fetch).toHaveBeenCalledOnce();
    for (const key of ['jwt_access', 'jwt_refresh', 'org'])
      expect(cookies.delete).toHaveBeenCalledWith(key, { path: '/' });
    expect(cookies.delete).not.toHaveBeenCalledWith('crm_invitation', expect.anything());
    expect(locals).toEqual({});
  }
);
