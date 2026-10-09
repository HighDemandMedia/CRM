import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
vi.mock('$lib/server/onboarding.js', () => ({ setupDestination: vi.fn() }));
vi.mock('$lib/server/password-session.js', () => ({ savePasswordSession: vi.fn() }));
vi.mock('$lib/server/v2/organization.js', () => ({ listTimezones: vi.fn() }));
vi.mock('$lib/server/v2/profile.js', () => ({ getProfile: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { actions } from './+page.server.js';
beforeEach(() => vi.resetAllMocks());
function event(service = 'calendar') {
  const form = new FormData();
  form.set('service', service);
  form.set('operation', 'sync');
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
