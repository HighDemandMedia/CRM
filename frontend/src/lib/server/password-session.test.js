import { describe, it, expect, vi } from 'vitest';
vi.mock('$env/dynamic/private', () => ({ env: { NODE_ENV: 'production' } }));
import { savePasswordSession, passwordError } from './password-session.js';

describe('password sessions', () => {
  it('stores credentials only in secure httpOnly cookies and selects the authorized organization', () => {
    const cookies = { set: vi.fn(), delete: vi.fn() };
    savePasswordSession(cookies, {
      access_token: 'access',
      refresh_token: 'refresh',
      current_org: { id: 'authorized-org' }
    });
    expect(cookies.set).toHaveBeenCalledWith(
      'jwt_access',
      'access',
      expect.objectContaining({ secure: true, httpOnly: true, sameSite: 'lax', maxAge: 3600 })
    );
    expect(cookies.set).toHaveBeenCalledWith(
      'jwt_refresh',
      'refresh',
      expect.objectContaining({ secure: true, httpOnly: true, maxAge: 14 * 86400 })
    );
    expect(cookies.delete).toHaveBeenCalledWith('org', { path: '/' });
    expect(cookies.set).toHaveBeenCalledWith('org', 'authorized-org', expect.anything());
  });
  it('removes the previous organization when the user must choose', () => {
    const cookies = { set: vi.fn(), delete: vi.fn() };
    savePasswordSession(cookies, {
      access_token: 'access',
      refresh_token: 'refresh',
      current_org: null
    });
    expect(cookies.delete).toHaveBeenCalledWith('org', { path: '/' });
    expect(cookies.set.mock.calls.some(([key]) => key === 'org')).toBe(false);
  });
  it('shows password rules without exposing request credentials in error messages', () => {
    expect(passwordError({ response: { data: { password: ['Too common.'] } } }, 'Failed')).toBe(
      'Too common.'
    );
    expect(passwordError({ config: { data: { password: 'secret' } } }, 'Failed')).toBe('Failed');
  });
});
