import { expect, it, vi, beforeEach } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { actions } from './+page.server.js';
beforeEach(() => vi.clearAllMocks());
async function save(changes) {
  const form = new FormData();
  form.set('changes', JSON.stringify(changes));
  return actions.saveFields(
    /** @type {any} */ ({
      cookies: {},
      params: { id: 'deal-id' },
      request: { formData: async () => form }
    })
  );
}
it('saves only edited properties without overwriting owner or associations', async () => {
  vi.mocked(apiRequest).mockResolvedValue({});
  expect(await save({ city: 'Miami' })).toEqual({ saved: true });
  expect(apiRequest).toHaveBeenCalledWith(
    '/opportunities/deal-id/',
    { method: 'PATCH', body: { city: 'Miami' } },
    { cookies: {} }
  );
});
it('rejects fields controlled by the server', async () => {
  const result = /** @type {any} */ (await save({ org: 'forged' }));
  expect(result.status).toBe(400);
  expect(apiRequest).not.toHaveBeenCalled();
});
it('reports save failures', async () => {
  vi.mocked(apiRequest).mockRejectedValue(new Error('Invalid association'));
  const result = /** @type {any} */ (await save({ account: '', contacts: [] }));
  expect(result.status).toBe(400);
  expect(result.data.error).toBeTruthy();
});
