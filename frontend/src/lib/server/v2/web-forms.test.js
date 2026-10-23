import { beforeEach, describe, expect, it, vi } from 'vitest';

const apiRequest = vi.fn();
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: (...args) => apiRequest(...args) }));
const { updateWebForm } = await import('./web-forms.js');
const event = /** @type {any} */ ({ cookies: {} });

describe('web form visitor confirmation settings', () => {
  beforeEach(() => apiRequest.mockReset());

  it.each([true, false])('preserves an explicit confirmation setting of %s', async (enabled) => {
    await updateWebForm(event, 'quote-form', {
      send_confirmation_email: enabled,
      org: 'another-organization',
      is_published: true
    });
    expect(apiRequest).toHaveBeenCalledWith(
      '/webforms/quote-form/',
      { method: 'PUT', body: { send_confirmation_email: enabled } },
      { cookies: event.cookies }
    );
  });

  it('does not reset the setting when saving unrelated fields', async () => {
    await updateWebForm(event, 'quote-form', { name: 'Quote' });
    expect(apiRequest.mock.calls[0][1].body).toEqual({ name: 'Quote' });
  });
});
