import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
vi.mock('$lib/server/v2/org-people.js', () => ({
  getOrgPeopleAndTeams: async () => ({ people: [] }),
  resolveMe: () => null
}));
vi.mock('$lib/server/v2/tags.js', () => ({ getTags: async () => ({ tags: [] }) }));
import { apiRequest } from '$lib/api-helpers.js';
import { load as contacts } from '../../../routes/(app)/contacts/+page.server.js';
import { load as companies } from '../../../routes/(app)/accounts/+page.server.js';
import { load as deals } from '../../../routes/(app)/pipeline/+page.server.js';
beforeEach(() => vi.resetAllMocks());
it.each([
  ['contacts', 'Contact', contacts],
  ['accounts', 'Account', companies],
  ['opportunities', 'Opportunity', deals]
])('loads %s board in one request with independent offsets', async (endpoint, target, load) => {
  vi.mocked(apiRequest).mockResolvedValue({
    board: [
      {
        key: 'CUSTOM',
        results: [{ id: 'record', name: 'Example', first_name: 'Example', tags: [] }],
        count: 40,
        offset: 25,
        money_totals: [{ currency: 'EUR', amount: '200' }]
      }
    ],
    count: 40,
    totals: { count: 40 },
    active_accounts: { open_accounts_count: 40 },
    stages: []
  });
  const result = await load(
    /** @type {any} */ ({
      cookies: {},
      locals: {},
      url: new URL('https://crm.example.com/?view=pipeline&CUSTOM_offset=25&search=Example'),
      parent: async () => ({
        pipelineConfig: { [target]: { stages: [{ key: 'CUSTOM', label: 'Review' }] } }
      })
    })
  );
  expect(apiRequest).toHaveBeenCalledOnce();
  const path = vi.mocked(apiRequest).mock.calls[0][0];
  expect(path.startsWith(`/${endpoint}/?`)).toBe(true);
  const query = new URL(path, 'https://api.example.com').searchParams;
  expect(query.get('board')).toBe('true');
  expect(query.get('limit')).toBe('25');
  expect(query.get('CUSTOM_offset')).toBe('25');
  expect(query.get('search')).toBe('Example');
  if (!result) throw new Error('Expected board data');
  expect(result.board[0]).toMatchObject({
    label: 'Review',
    value: 'CUSTOM',
    count: 40,
    offset: 25,
    moneyTotals: [{ currency: 'EUR', amount: '200' }],
    contacts: [{ id: 'record' }]
  });
});

it('keeps boards available while the previous API version is still deploying', async () => {
  const { pipelineColumns } = await import('./pipeline-columns.js');
  const list = vi
    .fn()
    .mockResolvedValue({ results: [{ id: 'old-api' }], totals: { count: 4, money_totals: [] } });
  const result = await pipelineColumns(
    {},
    [{ value: 'LEAD', label: 'Lead' }],
    new URLSearchParams('board=true&LEAD_offset=25&limit=25'),
    list
  );
  expect(result[0]).toMatchObject({
    value: 'LEAD',
    offset: 25,
    count: 4,
    contacts: [{ id: 'old-api' }]
  });
  expect(list.mock.calls[0][0].has('board')).toBe(false);
  expect(list.mock.calls[0][0].get('offset')).toBe('25');
});
