import { describe, it, expect, vi } from 'vitest';
vi.mock('$env/dynamic/private', () => ({ env: { NODE_ENV: 'production' } }));
import { savePasswordSession, saveSessionTokens, passwordError } from './password-session.js';

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

it('uses the same persistent lifetimes when rotating a session', () => {
  const cookies = { set: vi.fn(), delete: vi.fn() };
  saveSessionTokens(cookies, {
    access_token: 'access',
    refresh_token: 'rotated',
    current_org: { id: 'org' }
  });
  expect(cookies.set).toHaveBeenCalledWith(
    'jwt_access',
    'access',
    expect.objectContaining({ maxAge: 3600, secure: true, httpOnly: true })
  );
  expect(cookies.set).toHaveBeenCalledWith(
    'jwt_refresh',
    'rotated',
    expect.objectContaining({ maxAge: 14 * 86400 })
  );
  expect(cookies.set).toHaveBeenCalledWith(
    'org',
    'org',
    expect.objectContaining({ maxAge: 14 * 86400 })
  );
  expect(cookies.delete).not.toHaveBeenCalled();
});

it('does not overwrite a refresh cookie when no replacement was returned', () => {
  const cookies = { set: vi.fn(), delete: vi.fn() };
  saveSessionTokens(cookies, { access_token: 'access' });
  expect(cookies.set).toHaveBeenCalledTimes(1);
  expect(cookies.delete).not.toHaveBeenCalled();
});

function token(payload) {
  return `header.${Buffer.from(JSON.stringify(payload)).toString('base64url')}.signature`;
}

it('keeps unremembered access, refresh and organization cookies browser-session scoped', () => {
  const cookies = { set: vi.fn(), delete: vi.fn() };
  const payload = {
    remember_me: false,
    exp: Math.floor(Date.now() / 1000) + 3600,
    session_expires_at: Math.floor(Date.now() / 1000) + 28800
  };
  saveSessionTokens(cookies, {
    access_token: token(payload),
    refresh_token: token(payload),
    current_org: { id: 'org' }
  });
  expect(cookies.set).toHaveBeenCalledTimes(3);
  for (const [, , options] of cookies.set.mock.calls) {
    expect(options).not.toHaveProperty('maxAge');
    expect(options).not.toHaveProperty('expires');
    expect(options.httpOnly).toBe(true);
  }
});

it('uses remaining signed lifetime instead of extending remembered cookies', () => {
  const cookies = { set: vi.fn(), delete: vi.fn() };
  const deadline = Math.floor(Date.now() / 1000) + 60;
  const jwt = token({ remember_me: true, exp: deadline, session_expires_at: deadline });
  saveSessionTokens(cookies, { access_token: jwt, refresh_token: jwt, current_org: { id: 'org' } });
  for (const [, , options] of cookies.set.mock.calls) {
    expect(options.maxAge).toBeGreaterThanOrEqual(59);
    expect(options.maxAge).toBeLessThanOrEqual(60);
  }
});
