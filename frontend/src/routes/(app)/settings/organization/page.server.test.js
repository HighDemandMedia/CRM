import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
vi.mock('$lib/server/v2/organization.js', () => ({
  getOrgSettings: vi.fn(),
  listTimezones: vi.fn(),
  updateOrgSettings: vi.fn(),
  EDITABLE_FIELDS: []
}));
import { apiRequest } from '$lib/api-helpers.js';
import { getOrgSettings, listTimezones } from '$lib/server/v2/organization.js';
import { actions, load } from './+page.server.js';

beforeEach(() => vi.resetAllMocks());

it('leaves a closing organization readable but disables editing its settings', async () => {
  vi.mocked(getOrgSettings).mockResolvedValue(
    /** @type {any} */ ({ org: { lifecycle: { read_only: true } } })
  );
  vi.mocked(listTimezones).mockResolvedValue([]);
  const result = await load(
    /** @type {any} */ ({
      cookies: {},
      url: new URL('https://example.test/settings/organization'),
      parent: async () => ({ permissions: { is_admin: true } })
    })
  );
  if (!result) throw new Error('Expected organization settings');
  expect(result.can_edit).toBe(false);
});

it('sends a confirmed lifecycle action through the authenticated server API', async () => {
  const form = new FormData();
  form.set('action', 'reactivate');
  form.set('confirmation', 'Example organization');
  const cookies = {};
  const result = await actions.lifecycle(
    /** @type {any} */ ({ cookies, request: { formData: async () => form } })
  );
  expect(apiRequest).toHaveBeenCalledWith(
    '/org/lifecycle/',
    {
      method: 'POST',
      body: { action: 'reactivate', confirmation: 'Example organization' }
    },
    { cookies }
  );
  expect(result).toEqual({ lifecycleSaved: true });
});

it('shows a denied lifecycle operation as a form error without claiming success', async () => {
  vi.mocked(apiRequest).mockRejectedValue({
    status: 403,
    message: 'Only the organization owner or CRM owner can manage its closure.'
  });
  const result = await actions.lifecycle(
    /** @type {any} */ ({ cookies: {}, request: { formData: async () => new FormData() } })
  );
  if (!result) throw new Error('Expected a failed lifecycle action');
  expect(result.status).toBe(403);
  expect(result.data.scope).toBe('lifecycle');
  expect(result.data.lifecycleSaved).toBeUndefined();
});
