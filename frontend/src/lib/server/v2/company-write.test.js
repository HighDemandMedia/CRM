import { it, expect, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({
  apiRequest: vi.fn().mockResolvedValue({ id: 'company' })
}));
import { apiRequest } from '$lib/api-helpers.js';
import { createAccount, updateAccount } from './accounts.js';
it('normalizes domain and submits pages, contact and tag associations', async () => {
  await createAccount(/** @type {any} */ ({ cookies: {} }), {
    name: 'Test',
    website: 'example.com',
    pages: '[{"name":"Jobs","url":"https://example.com/jobs"}]',
    contacts: ['contact'],
    tags: ['tag'],
    number_of_employees: '12',
    annual_revenue: '120.50',
    assigned_to: 'owner'
  });
  expect(vi.mocked(apiRequest).mock.lastCall[1].body).toEqual({
    name: 'Test',
    website: 'https://example.com',
    pages: [{ name: 'Jobs', url: 'https://example.com/jobs' }],
    contacts: ['contact'],
    tag_ids: ['tag'],
    number_of_employees: 12,
    annual_revenue: 120.5,
    assigned_to: ['owner']
  });
});
it('source changes preserve omitted associations and allow clearing source', async () => {
  await updateAccount(/** @type {any} */ ({ cookies: {} }), 'company', { source: '' });
  expect(vi.mocked(apiRequest).mock.lastCall[1]).toEqual({
    method: 'PATCH',
    body: { source: null }
  });
});
