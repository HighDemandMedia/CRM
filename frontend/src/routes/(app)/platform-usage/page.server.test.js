import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { load } from './+page.server.js';
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
