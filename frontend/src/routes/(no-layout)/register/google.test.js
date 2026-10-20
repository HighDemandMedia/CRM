import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('axios', () => ({ default: { post: vi.fn() } }));
vi.mock('$env/dynamic/private', () => ({ env: { NODE_ENV: 'production' } }));
import axios from 'axios';
import { env } from '$env/dynamic/private';
import { actions, load } from './+page.server.js';
import { load as callback, actions as loginActions } from '../login/+page.server.js';
const token = 'google-invitation-test-982374';
const invitation = {
  email: 'invite@gmail.com',
  organization: 'Demo',
  legal: { version: 'v1', organization_authority_required: true }
};
// Partial SvelteKit event fixture; only the dependencies exercised by these handlers.
/** @returns {any} */
function event() {
  const values = new Map([['crm_invitation', token]]);
  const form = new FormData();
  for (const [key, value] of Object.entries({
    legal_version: 'v1',
    legal_locale: 'es',
    accept_terms: 'on',
    organization_authority: 'on'
  }))
    form.set(key, value);
  return {
    url: new URL('https://crm.example.com/register'),
    locals: {},
    getClientAddress: () => '198.51.100.23',
    request: { formData: async () => form },
    form,
    cookies: {
      get: (name) => values.get(name),
      set: vi.fn((name, value) => values.set(name, value)),
      delete: vi.fn((name) => values.delete(name))
    }
  };
}
beforeEach(() => {
  vi.clearAllMocks();
  env.GOOGLE_CLIENT_ID = 'test-client';
  env.GOOGLE_LOGIN_DOMAIN = 'https://crm.example.com';
  delete env.CRM_PROXY_SIGNING_KEY;
  vi.mocked(axios.post).mockResolvedValue({ data: invitation });
});
it('offers Google first and password as an explicit alternative', async () => {
  const e = event();
  expect(await load(e)).toMatchObject({ google_available: true, password: false });
  e.url.searchParams.set('method', 'password');
  expect(await load(e)).toMatchObject({ password: true });
});
it('requires current agreement and authority before leaving for Google', async () => {
  const e = event();
  e.form.delete('organization_authority');
  expect(await actions.google(e)).toMatchObject({ status: 400 });
  expect(e.cookies.set).not.toHaveBeenCalled();
});
it('requires a valid invitation even if Google is configured', async () => {
  const e = event();
  e.cookies.delete('crm_invitation');
  expect(await actions.google(e)).toMatchObject({ status: 403 });
  expect(axios.post).not.toHaveBeenCalled();
});
it('binds consent and invitation to PKCE and completes onboarding without a password', async () => {
  const e = event();
  let destination = '';
  try {
    await actions.google(e);
  } catch (error) {
    destination = error.location;
  }
  const url = new URL(destination);
  expect(url.searchParams.get('login_hint')).toBe(invitation.email);
  expect(url.searchParams.get('scope')).toBe('openid email profile');
  const context = JSON.parse(e.cookies.get('oauth_invitation'));
  expect(context).toMatchObject({
    token,
    state: e.cookies.get('oauth_state'),
    legal: { accept_terms: true, organization_authority: true, legal_locale: 'es' }
  });
  expect(e.cookies.set).toHaveBeenCalledWith(
    'oauth_invitation',
    expect.any(String),
    expect.objectContaining({ httpOnly: true, secure: true, sameSite: 'lax', maxAge: 600 })
  );
  vi.mocked(axios.post).mockResolvedValue({
    data: {
      access_token: 'access',
      refresh_token: 'refresh',
      current_org: { id: 'invited-org' },
      invitation_accepted: true
    }
  });
  e.url = new URL(
    'https://crm.example.com/login?code=google-code&state=' + e.cookies.get('oauth_state')
  );
  await expect(callback(e)).rejects.toMatchObject({ location: '/onboarding' });
  const body = JSON.parse(String(vi.mocked(axios.post).mock.lastCall[1]));
  expect(body).toMatchObject({
    invitation: token,
    accept_terms: true,
    organization_authority: true
  });
  expect(body).not.toHaveProperty('password');
  expect(e.cookies.get('crm_invitation')).toBeUndefined();
  expect(e.cookies.get('oauth_invitation')).toBeUndefined();
  expect(e.cookies.get('org')).toBe('invited-org');
});
it('rejects an invitation changed while Google is open', async () => {
  const e = event();
  await expect(actions.google(e)).rejects.toMatchObject({ status: 303 });
  e.url = new URL('https://crm.example.com/login?code=code&state=' + e.cookies.get('oauth_state'));
  e.cookies.set('crm_invitation', 'another-invitation-token-982374');
  vi.mocked(axios.post).mockClear();
  await expect(callback(e)).rejects.toMatchObject({ location: '/register?error=session_expired' });
  expect(axios.post).not.toHaveBeenCalled();
});
it('returns cancellation to invitation and clears temporary consent', async () => {
  const e = event();
  await expect(actions.google(e)).rejects.toMatchObject({ status: 303 });
  e.url = new URL('https://crm.example.com/login?error=access_denied');
  await expect(callback(e)).rejects.toMatchObject({ location: '/register?error=access_denied' });
  expect(e.cookies.get('oauth_invitation')).toBeUndefined();
  expect(e.cookies.get('crm_invitation')).toBe(token);
});
it('does not reuse invitation consent for an ordinary sign-in attempt', async () => {
  const e = event();
  await expect(actions.google(e)).rejects.toMatchObject({ status: 303 });
  await expect(loginActions.google(e)).rejects.toMatchObject({ status: 303 });
  expect(e.cookies.get('oauth_invitation')).toBeUndefined();
});
it('keeps the invitation after a rejected email and exposes no provider details', async () => {
  const e = event();
  await expect(actions.google(e)).rejects.toMatchObject({ status: 303 });
  e.url = new URL('https://crm.example.com/login?code=code&state=' + e.cookies.get('oauth_state'));
  vi.spyOn(console, 'error').mockImplementation(() => {});
  vi.mocked(axios.post).mockRejectedValue({
    response: { status: 400, data: { error: 'private provider detail' } }
  });
  await expect(callback(e)).rejects.toMatchObject({ location: '/register?error=auth_failed' });
  expect(e.cookies.get('crm_invitation')).toBe(token);
  expect(e.cookies.get('jwt_access')).toBeUndefined();
});
