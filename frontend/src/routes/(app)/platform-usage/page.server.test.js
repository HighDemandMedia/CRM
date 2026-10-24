import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { actions, load } from './+page.server.js';
const event = (isPlatformOwner) =>
  /** @type {any} */ ({
    parent: async () => ({ isPlatformOwner }),
    cookies: {},
    url: new URL('https://crm.example.com/platform-usage?q=Demo&page_size=10&org=other')
  });
beforeEach(() => vi.resetAllMocks());
it('denies organization admins before fetching cross-organization usage', async () => {
  await expect(load(event(false))).rejects.toMatchObject({ status: 403 });
  expect(apiRequest).not.toHaveBeenCalled();
});
it('passes only pagination and search to the owner API', async () => {
  vi.mocked(apiRequest).mockResolvedValue({ count: 1 });
  expect(await load(event(true))).toMatchObject({ usage: { count: 1 }, usageError: '' });
  expect(apiRequest).toHaveBeenCalledWith(
    '/platform/usage/?q=Demo&page_size=10',
    {},
    { cookies: {} }
  );
});
it('preserves backend permission denial after the shell loads', async () => {
  vi.mocked(apiRequest).mockRejectedValue({ status: 403 });
  await expect(load(event(true))).rejects.toMatchObject({ status: 403 });
});
it('returns a recoverable error without fabricated metrics', async () => {
  vi.mocked(apiRequest).mockRejectedValue(new Error('offline'));
  expect(await load(event(true))).toMatchObject({
    usage: null,
    usageError: 'Could not load usage.'
  });
});

function limitEvent(values = {}) {
  const form = new FormData();
  form.set('organization_id', '12345678-1234-1234-1234-123456789012');
  for (const [key, value] of Object.entries(values)) form.set(key, value);
  return /** @type {any} */ ({ request: { formData: async () => form }, cookies: {} });
}

it('saves zero and unlimited as distinct choices', async () => {
  expect(await actions.limits(limitEvent({ users: '5', contacts: '0', tasks: '' }))).toEqual({
    limitsSaved: true
  });
  expect(apiRequest).toHaveBeenCalledWith(
    '/platform/organizations/12345678-1234-1234-1234-123456789012/limits/',
    {
      method: 'PATCH',
      body: {
        limits: {
          users: 5,
          contacts: 0,
          companies: null,
          deals: null,
          tasks: null,
          tickets: null,
          appointments: null
        }
      }
    },
    { cookies: {} }
  );
});

it.each(['-1', '1.5', 'Infinity', '2147483648', '5e3'])(
  'rejects invalid quotas: %s',
  async (users) => {
    const result = await actions.limits(limitEvent({ users }));
    expect(result).toMatchObject({ status: 400 });
    expect(apiRequest).not.toHaveBeenCalled();
  }
);

it('keeps the dialog error when the server denies owner access', async () => {
  vi.mocked(apiRequest).mockRejectedValue(
    Object.assign(new Error('Access denied.'), { status: 403 })
  );
  expect(await actions.limits(limitEvent())).toMatchObject({
    status: 403,
    data: { limitsError: 'Access denied.' }
  });
});
