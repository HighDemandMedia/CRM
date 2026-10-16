import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('$lib/server/v2/contacts.js', () => ({ getContactForEdit: vi.fn() }));
import { getContactForEdit } from '$lib/server/v2/contacts.js';
import { GET } from './+server.js';
const id = '11111111-1111-4111-8111-111111111111';
const event = (recordId = id) => /** @type {any} */ ({ cookies: {}, params: { id: recordId } });
beforeEach(() => vi.resetAllMocks());
it('loads options only for the authenticated record without public caching', async () => {
  vi.mocked(getContactForEdit).mockResolvedValue(/** @type {any} */ ({ contact: { id } }));
  const response = await GET(event());
  expect(getContactForEdit).toHaveBeenCalledExactlyOnceWith({ cookies: {} }, id);
  expect(response.headers.get('cache-control')).toBe('private, no-store');
});
it('rejects a path in place of a record ID', async () => {
  expect((await GET(event('../other'))).status).toBe(400);
  expect(getContactForEdit).not.toHaveBeenCalled();
});
it.each([401, 403, 404, 429, 500])(
  'preserves access denial and hides internal errors (%s)',
  async (status) => {
    vi.mocked(getContactForEdit).mockRejectedValue({ status, message: 'private error' });
    const response = await GET(event());
    expect(response.status).toBe(status === 500 ? 503 : status);
    expect(await response.text()).not.toContain('private error');
  }
);
