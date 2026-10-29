import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { GET } from './+server.js';

beforeEach(() => vi.clearAllMocks());

it('checks only the personal calendar revision without fetching all objects', async () => {
  vi.mocked(apiRequest).mockResolvedValue({ revision: 'version-one' });
  const cookies = {};
  const response = await GET(
    /** @type {any} */ ({ cookies, url: new URL('https://crm.test/calendar/events?view=status') })
  );
  expect(await response.json()).toEqual({ revision: 'version-one' });
  expect(response.headers.get('Cache-Control')).toBe('private, no-store');
  expect(apiRequest).toHaveBeenCalledExactlyOnceWith(
    '/integrations/google/events/?view=status',
    {},
    { cookies }
  );
});

it.each([401, 403, 404, 500])(
  'preserves access failures and masks internal errors (%s)',
  async (status) => {
    vi.mocked(apiRequest).mockRejectedValue(
      Object.assign(new Error('Internal provider details'), { status })
    );
    await expect(
      GET(
        /** @type {any} */ ({
          cookies: {},
          url: new URL('https://crm.test/calendar/events?view=status')
        })
      )
    ).rejects.toMatchObject({
      status: status === 500 ? 503 : status,
      body: { message: 'Calendar status unavailable.' }
    });
  }
);
