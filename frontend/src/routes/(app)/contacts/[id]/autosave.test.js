import { expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { actions } from './+page.server.js';
it('uses a partial update and ignores server-owned fields', async () => {
  vi.mocked(apiRequest).mockResolvedValue({});
  const form = new FormData();
  form.set('changes', JSON.stringify({ city: 'Boston', org: 'forged', created_by: 'forged' }));
  const result = await actions.saveFields(
    /** @type {any} */ ({
      cookies: {},
      params: { id: 'contact-id' },
      request: { formData: async () => form }
    })
  );
  expect(result).toEqual({ saved: true });
  expect(apiRequest).toHaveBeenCalledWith(
    '/contacts/contact-id/',
    { method: 'PATCH', body: { city: 'Boston' } },
    { cookies: {} }
  );
});
it('surfaces validation errors instead of claiming a save', async () => {
  vi.mocked(apiRequest).mockRejectedValue(new Error('Invalid phone'));
  const form = new FormData();
  form.set('changes', '{"phone":""}');
  const result = /** @type {any} */ (
    await actions.saveFields(
      /** @type {any} */ ({
        cookies: {},
        params: { id: 'contact-id' },
        request: { formData: async () => form }
      })
    )
  );
  expect(result.status).toBe(400);
  expect(result.data.error).toBeTruthy();
});
