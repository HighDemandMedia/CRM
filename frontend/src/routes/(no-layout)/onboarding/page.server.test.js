import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
vi.mock('$lib/server/v2/organization.js', () => ({
  listTimezones: vi.fn(async () => []),
  updateOrgSettings: vi.fn()
}));
import { apiRequest } from '$lib/api-helpers.js';
import { updateOrgSettings } from '$lib/server/v2/organization.js';
import { load, actions } from './+page.server.js';

function event(fields = {}) {
  const form = new FormData();
  for (const [key, value] of Object.entries(fields)) form.set(key, String(value));
  return /** @type {any} */ ({
    cookies: { get: vi.fn(), set: vi.fn() },
    setHeaders: vi.fn(),
    url: new URL('https://crm.example.com/onboarding'),
    request: { url: 'https://crm.example.com/onboarding', formData: async () => form }
  });
}
beforeEach(() => vi.resetAllMocks());
const admin = { setup_step: 'organization', permissions: { is_admin: true } };
it('loads only personal setup for a team member without accessing organization settings', async () => {
  vi.mocked(apiRequest)
    .mockResolvedValueOnce({ setup_step: 'profile' })
    .mockResolvedValueOnce({ user_obj: { name: 'Member' } });
  expect(await load(event())).toMatchObject({ step: 'profile', includesOrganization: false });
  expect(apiRequest).toHaveBeenCalledTimes(2);
});
it('resumes the saved organization step and permits returning to the profile', async () => {
  vi.mocked(apiRequest)
    .mockResolvedValueOnce(admin)
    .mockResolvedValueOnce({ user_obj: {} })
    .mockResolvedValueOnce({ name: 'Company' });
  expect(await load(event())).toMatchObject({
    step: 'organization',
    organization: { name: 'Company' }
  });
  vi.mocked(apiRequest).mockResolvedValueOnce(admin).mockResolvedValueOnce({ user_obj: {} });
  const back = event();
  back.url.searchParams.set('step', 'profile');
  expect(await load(back)).toMatchObject({
    step: 'profile',
    includesOrganization: true,
    organization: null
  });
});
it.each([{ setup_step: 'complete' }, { setup_step: 'profile', lifecycle: { read_only: true } }])(
  'does not trap completed or closed accounts in setup',
  async (context) => {
    vi.mocked(apiRequest).mockResolvedValue(context);
    await expect(load(event())).rejects.toMatchObject({ status: 303, location: '/' });
  }
);
it('does not allow a member or a forged step to edit organization settings', async () => {
  vi.mocked(apiRequest).mockResolvedValueOnce({
    setup_step: 'profile',
    permissions: { is_admin: false }
  });
  await expect(actions.default(event({ step: 'organization' }))).rejects.toMatchObject({
    status: 403
  });
  expect(updateOrgSettings).not.toHaveBeenCalled();
});
it('does not allow an owner to skip required profile setup', async () => {
  vi.mocked(apiRequest).mockResolvedValueOnce({ ...admin, setup_step: 'profile_organization' });
  expect(await actions.default(event({ step: 'organization' }))).toMatchObject({ status: 400 });
  expect(updateOrgSettings).not.toHaveBeenCalled();
});
it('saves only allowed personal fields and follows the server-owned next step', async () => {
  vi.mocked(apiRequest)
    .mockResolvedValueOnce({ setup_step: 'profile_organization' })
    .mockResolvedValueOnce({ setup_step: 'organization' });
  await expect(
    actions.default(
      event({
        step: 'profile',
        name: 'Name',
        ui_language: 'es',
        timezone: 'UTC',
        role: 'ADMIN',
        setup_step: 'complete'
      })
    )
  ).rejects.toMatchObject({ location: '/onboarding' });
  expect(apiRequest).toHaveBeenLastCalledWith(
    '/profile/',
    {
      method: 'PATCH',
      body: { name: 'Name', ui_language: 'es', timezone: 'UTC', complete_setup: true }
    },
    expect.anything()
  );
});
it('keeps values and field errors after failed validation', async () => {
  vi.mocked(apiRequest)
    .mockResolvedValueOnce({ setup_step: 'profile' })
    .mockRejectedValueOnce({
      status: 400,
      body: { timezone: ['Invalid time zone.'] },
      message: 'Invalid time zone.'
    });
  expect(
    await actions.default(
      event({ step: 'profile', name: 'Name', timezone: 'bad', ui_language: 'en' })
    )
  ).toMatchObject({
    status: 400,
    data: { values: { name: 'Name' }, errors: { timezone: 'Invalid time zone.' } }
  });
});
it('does not expose internal server errors or leave setup after a failed save', async () => {
  vi.mocked(apiRequest).mockResolvedValueOnce(admin);
  vi.mocked(updateOrgSettings).mockRejectedValueOnce(new Error('internal secret'));
  const result = await actions.default(event({ step: 'organization', name: 'Company' }));
  expect(result).toMatchObject({ status: 503, data: { values: { name: 'Company' } } });
  expect(JSON.stringify(result)).not.toContain('internal secret');
});
it('opens the CRM only after organization settings save successfully', async () => {
  vi.mocked(apiRequest).mockResolvedValueOnce(admin);
  vi.mocked(updateOrgSettings).mockResolvedValueOnce({});
  await expect(
    actions.default(
      event({
        step: 'organization',
        name: 'Company',
        timezone: 'UTC',
        default_currency: 'USD',
        default_country: 'US'
      })
    )
  ).rejects.toMatchObject({ status: 303, location: '/' });
});
