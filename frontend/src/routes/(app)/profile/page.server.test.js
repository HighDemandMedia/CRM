import { beforeEach, describe, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
import { apiRequest } from '$lib/api-helpers.js';
import { actions } from './+page.server.js';

beforeEach(() => vi.clearAllMocks());
function event(values) {
  const form = new FormData();
  for (const [key, value] of Object.entries(values)) form.set(key, String(value));
  return /** @type {any} */ ({ cookies: {}, request: { formData: async () => form } });
}

describe('profile setup confirmation', () => {
  it.each([
    ['complete', '/'],
    ['organization', '/settings/organization']
  ])('continues from the API state %s', async (step, destination) => {
    vi.mocked(apiRequest).mockResolvedValue({ setup_step: step });
    await expect(
      actions.edit(
        event({
          complete_setup: '1',
          name: ' Invited Person ',
          ui_language: 'es',
          timezone: '',
          role: 'ADMIN',
          org: 'other-org',
          setup_step: 'complete'
        })
      )
    ).rejects.toMatchObject({ status: 303, location: destination });
    expect(apiRequest).toHaveBeenCalledWith(
      '/profile/',
      {
        method: 'PATCH',
        body: { complete_setup: true, name: 'Invited Person', ui_language: 'es', timezone: '' }
      },
      expect.anything()
    );
  });
  it('keeps validation failures on the profile with entered values', async () => {
    vi.mocked(apiRequest).mockRejectedValue({
      status: 400,
      data: { name: ['Enter your full name.'] }
    });
    const result = await actions.edit(event({ complete_setup: '1', name: ' ' }));
    expect(result).toMatchObject({
      status: 400,
      data: { values: { name: '', complete_setup: true } }
    });
  });
  it('keeps regular profile editing on the page', async () => {
    vi.mocked(apiRequest).mockResolvedValue({ setup_step: 'complete' });
    expect(await actions.edit(event({ name: 'Updated Name' }))).toEqual({ saved: true });
    expect(apiRequest).toHaveBeenCalledWith(
      '/profile/',
      {
        method: 'PATCH',
        body: { name: 'Updated Name' }
      },
      expect.anything()
    );
  });
});
