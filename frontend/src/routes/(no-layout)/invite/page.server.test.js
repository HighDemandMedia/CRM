import { beforeEach, describe, expect, it, vi } from 'vitest';
vi.mock('axios', () => ({ default: { post: vi.fn() } }));
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
vi.mock('$env/dynamic/private', () => ({ env: { NODE_ENV: 'production' } }));
import axios from 'axios';
import { env } from '$env/dynamic/private';
import { load, actions as inviteActions } from './+page.server.js';
import { apiRequest } from '$lib/api-helpers.js';
import { load as registerLoad, actions } from '../register/+page.server.js';

beforeEach(() => {
  delete env.CRM_PROXY_SIGNING_KEY;
  vi.clearAllMocks();
});

/** @returns {any} */
function event(token = 'valid-invitation-token-982734') {
  return {
    url: new URL('https://crm.example.com/invite'),
    locals: {},
    request: { formData: async () => new FormData() },
    cookies: {
      get: vi.fn((key) => (key === 'crm_invitation' ? token : undefined)),
      set: vi.fn(),
      delete: vi.fn()
    }
  };
}
const invitation = {
  email: 'invited@example.com',
  organization: 'Inviting Organization',
  existing_account: false
};

describe('invitation onboarding', () => {
  it('stores the emailed token securely and removes it from the URL', async () => {
    const input = event();
    input.url.searchParams.set('token', 'valid-invitation-token-982734');
    await expect(load(input)).rejects.toMatchObject({ status: 303, location: '/invite' });
    expect(input.cookies.set).toHaveBeenCalledWith(
      'crm_invitation',
      'valid-invitation-token-982734',
      expect.objectContaining({ httpOnly: true, secure: true, sameSite: 'lax' })
    );
  });
  it('takes new invitees directly to password creation with verified email and organization', async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: invitation });
    await expect(load(event())).rejects.toMatchObject({ status: 303, location: '/register' });
    expect(await registerLoad(event())).toEqual({ invited: true, invitation });
  });
  it('keeps existing users on the sign-in and acceptance flow', async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: { ...invitation, existing_account: true } });
    expect(await load(event())).toMatchObject({
      signedIn: false,
      invitation: { existing_account: true }
    });
    await expect(registerLoad(event())).rejects.toMatchObject({ status: 303, location: '/invite' });
  });
  it('shows invalid invitation errors without routing users into public registration', async () => {
    vi.mocked(axios.post).mockRejectedValue({
      response: { data: { error: 'Invitation expired.' } }
    });
    expect(await load(event())).toMatchObject({ error: 'Invitation expired.' });
    expect(await registerLoad(event())).toEqual({ invited: true, error: 'Invitation expired.' });
  });
  it('does not request invitation details without a token', async () => {
    expect(await registerLoad(event(''))).toEqual({ invited: false });
    expect(axios.post).not.toHaveBeenCalled();
  });
  it.each([false, true])(
    'joins with the invitation and routes initial administrators to setup (%s)',
    async (needsSetup) => {
      env.CRM_PROXY_SIGNING_KEY = 'ab'.repeat(32);
      const input = event();
      input.getClientAddress = () => '198.51.100.10';
      const form = new FormData();
      for (const [key, value] of Object.entries({
        name: 'Invited User',
        email: invitation.email,
        password: 'A-safe-password-2938!',
        confirm_password: 'A-safe-password-2938!',
        legal_version: '2026-10-12',
        legal_locale: 'en',
        accept_terms: 'on',
        organization_authority: 'on'
      }))
        form.set(key, value);
      input.request = { formData: async () => form };
      vi.mocked(axios.post).mockResolvedValue({
        data: {
          access_token: 'access',
          refresh_token: 'refresh',
          current_org: { id: 'invited-org' },
          needs_organization_setup: needsSetup
        }
      });
      await expect(actions.default(input)).rejects.toMatchObject({
        status: 303,
        location: '/onboarding'
      });
      const [url, body, config] = vi.mocked(axios.post).mock.calls[0];
      expect(url).toContain('/auth/password/register/');
      const payload = JSON.parse(String(body));
      expect(payload).toMatchObject({
        invitation: 'valid-invitation-token-982734',
        email: invitation.email,
        legal_version: '2026-10-12',
        legal_locale: 'en',
        accept_terms: true,
        organization_authority: true
      });
      expect(config?.headers).toMatchObject({
        'Content-Type': 'application/json',
        'X-CRM-Client-IP': '198.51.100.10',
        'X-CRM-Client-Signature': expect.stringMatching(/^[0-9a-f]{64}$/)
      });
      expect(input.cookies.set).toHaveBeenCalledWith('org', 'invited-org', expect.anything());
      expect(payload).not.toHaveProperty('organization');
      expect(input.cookies.delete).toHaveBeenCalledWith('crm_invitation', { path: '/' });
    }
  );
});

it.each([false, true])(
  'switches existing invitees to the invited organization before setup (%s)',
  async (needsSetup) => {
    const input = event();
    vi.mocked(apiRequest)
      .mockResolvedValueOnce({ org_id: 'customer-org', needs_organization_setup: needsSetup })
      .mockResolvedValueOnce({ access_token: 'new-access', refresh_token: 'new-refresh' });
    await expect(inviteActions.accept(input)).rejects.toMatchObject({
      status: 303,
      location: '/onboarding'
    });
    expect(input.cookies.set).toHaveBeenCalledWith('org', 'customer-org', expect.anything());
  }
);

it('does not call registration without an invitation cookie', async () => {
  const input = event('');
  input.request = { formData: async () => new FormData() };
  expect(await actions.default(input)).toMatchObject({ status: 403 });
  expect(axios.post).not.toHaveBeenCalled();
});

it('passes explicit acceptance and the displayed version to the existing-user API', async () => {
  const input = event();
  const form = new FormData();
  form.set('legal_version', '2026-10-12');
  form.set('legal_locale', 'es');
  form.set('accept_terms', 'on');
  form.set('organization_authority', 'on');
  input.request = { formData: async () => form };
  vi.mocked(apiRequest).mockResolvedValueOnce({});
  await expect(inviteActions.accept(input)).rejects.toMatchObject({ status: 303 });
  expect(apiRequest).toHaveBeenCalledWith(
    '/auth/accept-invitation/',
    {
      method: 'POST',
      body: {
        token: 'valid-invitation-token-982734',
        legal_version: '2026-10-12',
        legal_locale: 'es',
        accept_terms: true,
        organization_authority: true
      }
    },
    { cookies: input.cookies }
  );
});

it('preserves the invitation when legal acceptance is rejected', async () => {
  const input = event();
  vi.mocked(apiRequest).mockRejectedValueOnce(
    new Error('Accept the CRM Terms of Service to continue.')
  );
  expect(await inviteActions.accept(input)).toMatchObject({
    status: 400,
    data: {
      error: 'Accept the CRM Terms of Service to continue.'
    }
  });
  expect(input.cookies.delete).not.toHaveBeenCalled();
  expect(apiRequest).toHaveBeenCalledTimes(1);
});

it('offers a deliberate account switch instead of an error for another signed-in user', async () => {
  const input = event();
  input.locals.user = { email: 'owner@example.com' };
  vi.mocked(axios.post).mockResolvedValue({ data: invitation });
  vi.mocked(apiRequest).mockRejectedValueOnce({
    status: 403,
    body: { error: 'Sign in with the email address that received this invitation.' }
  });
  expect(await load(input)).toMatchObject({ differentAccount: true, error: '', invitation });
  expect(input.cookies.delete).not.toHaveBeenCalled();
});

it('signs invitation previews so visitors do not share the Web server throttle bucket', async () => {
  env.CRM_PROXY_SIGNING_KEY = 'ab'.repeat(32);
  const input = event();
  input.getClientAddress = () => '198.51.100.12';
  vi.mocked(axios.post).mockResolvedValue({ data: invitation });
  await expect(load(input)).rejects.toMatchObject({ location: '/register' });
  const [, body, config] = vi.mocked(axios.post).mock.calls[0];
  expect(JSON.parse(String(body))).toEqual({ token: 'valid-invitation-token-982734' });
  expect(config.headers).toMatchObject({
    'X-CRM-Client-IP': '198.51.100.12',
    'X-CRM-Client-Signature': expect.stringMatching(/^[0-9a-f]{64}$/)
  });
});
