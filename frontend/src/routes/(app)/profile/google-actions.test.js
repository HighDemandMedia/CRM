import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
vi.mock('$lib/server/onboarding.js', () => ({ setupDestination: vi.fn() }));
vi.mock('$lib/server/password-session.js', () => ({ savePasswordSession: vi.fn() }));
vi.mock('$lib/server/v2/organization.js', () => ({ listTimezones: vi.fn() }));
vi.mock('$lib/server/v2/profile.js', () => ({ getProfile: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { actions } from './+page.server.js';
beforeEach(() => vi.resetAllMocks());
function event(service = 'calendar', extra = {}) {
  const form = new FormData();
  form.set('service', service);
  form.set('operation', 'sync');
  form.set('disclosure_accepted', 'yes');
  for (const [key, value] of Object.entries(extra)) form.set(key, value);
  return /** @type {any} */ ({
    request: { formData: async () => form },
    cookies: {},
    url: new URL('https://crm.example.com/profile')
  });
}
it.each(['gmail', 'calendar'])('keeps %s sync API failures in the Google form', async (service) => {
  vi.mocked(apiRequest).mockRejectedValue(new Error('Internal Error: private upstream payload'));
  expect(await actions.googleManage(event(service))).toMatchObject({
    status: 400,
    data: {
      scope: 'google',
      message: 'Google is unavailable. Try syncing again later.'
    }
  });
});
it('shows safe setup feedback when connecting fails', async () => {
  vi.mocked(apiRequest).mockRejectedValue({
    body: ['Google connections need configuration by the CRM administrator.']
  });
  expect(await actions.googleConnect(event())).toMatchObject({
    data: {
      scope: 'google',
      message: 'Google connections need configuration by the CRM administrator.'
    }
  });
});
it('acknowledges a sync request without claiming it has finished', async () => {
  vi.mocked(apiRequest).mockResolvedValue({ queued: true });
  expect(await actions.googleManage(event())).toMatchObject({
    saved: true,
    scope: 'google',
    googleMessage:
      'Synchronization requested. Check the connection status and last sync time for progress.'
  });
});

it('does not start OAuth without explicit disclosure acceptance', async () => {
  expect(await actions.googleConnect(event('gmail', { disclosure_accepted: '' }))).toMatchObject({
    status: 400
  });
  expect(apiRequest).not.toHaveBeenCalled();
});
it('forwards explicit revoke confirmation and reports the correct outcome', async () => {
  vi.mocked(apiRequest).mockResolvedValue({ revoked: true });
  expect(
    await actions.googleManage(event('gmail', { operation: 'revoke', confirm_revoke: 'yes' }))
  ).toMatchObject({
    googleMessage: 'Google access removed. Reconnect any HDM integration you want to use again.'
  });
  expect(apiRequest).toHaveBeenCalledWith(
    '/integrations/google/',
    expect.objectContaining({
      body: expect.objectContaining({ confirm_revoke: true, operation: 'revoke' })
    }),
    expect.anything()
  );
});
it('only accepts the exact affirmative confirmation', async () => {
  vi.mocked(apiRequest).mockResolvedValue({ queued: true });
  await actions.googleManage(event('gmail', { operation: 'revoke', confirm_revoke: 'false' }));
  expect(apiRequest).toHaveBeenCalledWith(
    '/integrations/google/',
    expect.objectContaining({ body: expect.objectContaining({ confirm_revoke: false }) }),
    expect.anything()
  );
});

it.each(['gmail', 'calendar'])(
  'preserves the %s OAuth redirect and state cookie after disclosure',
  async (service) => {
    const input = event(service);
    input.cookies.set = vi.fn();
    vi.mocked(apiRequest).mockResolvedValue({
      state: 'test-state',
      url: 'https://accounts.google.com/o/oauth2/v2/auth?state=test-state'
    });
    await expect(actions.googleConnect(input)).rejects.toMatchObject({
      status: 303,
      location: 'https://accounts.google.com/o/oauth2/v2/auth?state=test-state'
    });
    expect(apiRequest).toHaveBeenCalledWith(
      `/integrations/google/connect/${service}/`,
      { method: 'POST', body: { disclosure_accepted: true } },
      { cookies: input.cookies }
    );
    expect(input.cookies.set).toHaveBeenCalledWith(
      'google_connection_state',
      'test-state',
      expect.objectContaining({
        httpOnly: true,
        secure: true,
        sameSite: 'lax',
        path: '/profile/google/callback',
        maxAge: 600
      })
    );
  }
);

it.each(['gmail', 'calendar'])(
  'disconnects only the selected %s service without revocation',
  async (service) => {
    vi.mocked(apiRequest).mockResolvedValue({ disconnected: true });
    expect(await actions.googleManage(event(service, { operation: 'disconnect' }))).toMatchObject({
      saved: true,
      googleMessage: 'Disconnected. Cached Google data has been removed from the CRM.'
    });
    expect(apiRequest).toHaveBeenCalledWith(
      '/integrations/google/',
      expect.objectContaining({
        body: expect.objectContaining({ service, operation: 'disconnect', confirm_revoke: false })
      }),
      expect.anything()
    );
  }
);
