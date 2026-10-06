import { beforeEach, describe, expect, it, vi } from 'vitest';
vi.mock('axios', () => ({ default: { post: vi.fn() } }));
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
vi.mock('$env/dynamic/private', () => ({ env: { NODE_ENV: 'production' } }));
import axios from 'axios';
import { load, actions as inviteActions } from './+page.server.js';
import { apiRequest } from '$lib/api-helpers.js';
import { load as registerLoad, actions } from '../register/+page.server.js';

beforeEach(() => vi.clearAllMocks());

/** @returns {any} */
function event(token = 'valid-invitation-token-982734') {
  return {
    url: new URL('https://crm.example.com/invite'),
    locals: {},
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
      const input = event();
      const form = new FormData();
      for (const [key, value] of Object.entries({
        name: 'Invited User',
        email: invitation.email,
        password: 'A-safe-password-2938!',
        confirm_password: 'A-safe-password-2938!'
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
        location: needsSetup ? '/settings/organization?onboarding=1' : '/'
      });
      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining('/auth/password/register/'),
        expect.objectContaining({
          invitation: 'valid-invitation-token-982734',
          email: invitation.email
        }),
        expect.anything()
      );
      expect(input.cookies.set).toHaveBeenCalledWith('org', 'invited-org', expect.anything());
      expect(vi.mocked(axios.post).mock.calls[0][1]).not.toHaveProperty('organization');
      expect(input.cookies.delete).toHaveBeenCalledWith('crm_invitation', { path: '/' });
    }
  );
});

it('switches existing invitees to the invited organization before setup', async () => {
  const input = event();
  vi.mocked(apiRequest)
    .mockResolvedValueOnce({ org_id: 'customer-org', needs_organization_setup: true })
    .mockResolvedValueOnce({ access_token: 'new-access', refresh_token: 'new-refresh' });
  await expect(inviteActions.accept(input)).rejects.toMatchObject({
    status: 303,
    location: '/settings/organization?onboarding=1'
  });
  expect(input.cookies.set).toHaveBeenCalledWith('org', 'customer-org', expect.anything());
});

it('does not call registration without an invitation cookie', async () => {
  const input = event('');
  input.request = { formData: async () => new FormData() };
  expect(await actions.default(input)).toMatchObject({ status: 403 });
  expect(axios.post).not.toHaveBeenCalled();
});
