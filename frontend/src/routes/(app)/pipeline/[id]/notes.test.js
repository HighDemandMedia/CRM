import { expect, it, vi, beforeEach } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { actions } from './+page.server.js';
beforeEach(() => vi.clearAllMocks());
async function addNote(comment) {
  const form = new FormData();
  form.set('comment', comment);
  return actions.note(
    /** @type {any} */ ({
      cookies: {},
      params: { id: 'deal-id' },
      request: { formData: async () => form }
    })
  );
}
it('creates a separate note without overwriting the description', async () => {
  vi.mocked(apiRequest).mockResolvedValue({});
  expect(await addNote(' Follow up tomorrow ')).toEqual({ noted: true });
  expect(apiRequest).toHaveBeenCalledWith(
    '/opportunities/deal-id/',
    { method: 'POST', body: { comment: 'Follow up tomorrow' } },
    { cookies: {} }
  );
});
it('rejects empty notes', async () => {
  const result = /** @type {any} */ (await addNote('   '));
  expect(result.status).toBe(400);
  expect(apiRequest).not.toHaveBeenCalled();
});
it('reports save failures', async () => {
  vi.mocked(apiRequest).mockRejectedValue(new Error('Unavailable'));
  const result = /** @type {any} */ (await addNote('Call tomorrow'));
  expect(result.status).toBe(400);
  expect(result.data.message).toBeTruthy();
});
