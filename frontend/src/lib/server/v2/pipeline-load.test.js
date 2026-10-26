import { beforeEach, expect, it, vi } from 'vitest';
vi.mock('$lib/api-helpers.js', () => ({ apiRequest: vi.fn() }));
vi.mock('$lib/server/v2/org-people.js', () => ({
  getOrgPeopleAndTeams: async () => ({ people: [] }),
  resolveMe: () => null
}));
vi.mock('$lib/server/v2/tags.js', () => ({ getTags: async () => ({ tags: [] }) }));
import { pipelinePresentation } from '$lib/v2/pipeline-presentation.js';
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
  const parent = vi.fn(() => {
    throw new Error('Batched board must not reload layouts');
  });
  const result = await load(
    /** @type {any} */ ({
      cookies: {},
      depends: vi.fn(),
      locals: {},
      url: new URL('https://crm.example.com/?view=pipeline&CUSTOM_offset=25&search=Example'),
      parent
    })
  );
  expect(apiRequest).toHaveBeenCalledOnce();
  expect(parent).not.toHaveBeenCalled();
  const path = vi.mocked(apiRequest).mock.calls[0][0];
  expect(path.startsWith(`/${endpoint}/?`)).toBe(true);
  const query = new URL(path, 'https://api.example.com').searchParams;
  expect(query.get('board')).toBe('true');
  expect(query.get('limit')).toBe('25');
  expect(query.get('CUSTOM_offset')).toBe('25');
  expect(query.get('search')).toBe('Example');
  if (!result) throw new Error('Expected board data');
  const presented = pipelinePresentation(
    result,
    { [target]: { stages: [{ key: 'CUSTOM', label: 'Review' }] } },
    target
  );
  expect(presented.board[0]).toMatchObject({
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

it('loads configured stages for an older API instead of silently losing custom columns', async () => {
  vi.mocked(apiRequest).mockResolvedValue({
    active_accounts: { open_accounts_count: 40, open_accounts: [] }
  });
  const parent = vi.fn().mockResolvedValue({
    pipelineConfig: { Account: { stages: [{ key: 'CUSTOM', label: 'Review' }] } }
  });
  const result = await companies(
    /** @type {any} */ ({
      cookies: {},
      depends: vi.fn(),
      parent,
      url: new URL('https://crm.example.com/accounts?view=pipeline&CUSTOM_offset=25')
    })
  );
  expect(parent).toHaveBeenCalledOnce();
  expect(apiRequest).toHaveBeenCalledTimes(2);
  expect(result).toMatchObject({
    board: [{ value: 'CUSTOM', label: 'Review', count: 40, offset: 25 }]
  });
});

it.each([
  ['contacts', contacts],
  ['accounts', companies],
  ['opportunities', deals]
])('keeps %s filters and paging without repeating parent loads', async (endpoint, load) => {
  vi.mocked(apiRequest).mockResolvedValue({
    results: [],
    count: 80,
    totals: { count: 80 },
    active_accounts: { open_accounts_count: 80 }
  });
  const parent = vi.fn(() => {
    throw new Error('Unexpected server parent');
  });
  const result = await load(
    /** @type {any} */ ({
      cookies: {},
      depends: vi.fn(),
      parent,
      url: new URL(
        'https://crm.example.com/?search=Example&assigned_to=aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa&tags=bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb&sort=name&direction=desc&page_size=10&offset=10'
      )
    })
  );
  expect(parent).not.toHaveBeenCalled();
  const query = new URL(vi.mocked(apiRequest).mock.calls[0][0], 'https://api.example.com')
    .searchParams;
  expect(query.get('search')).toBe('Example');
  expect(query.get('assigned_to')).toBe('aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
  expect(query.get('tags')).toBe('bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb');
  expect(query.get('offset')).toBe('10');
  expect(query.has('board')).toBe(false);
  expect(result).toMatchObject({ view: 'list', board: [], offset: 10 });
});

it.each([contacts, companies, deals])(
  'propagates record access denial without falling back to cached records',
  async (load) => {
    const denied = Object.assign(new Error('Forbidden'), { status: 403 });
    vi.mocked(apiRequest).mockRejectedValue(denied);
    await expect(
      load(
        /** @type {any} */ ({
          cookies: {},
          depends: vi.fn(),
          url: new URL('https://crm.example.com/?view=pipeline'),
          parent: vi.fn()
        })
      )
    ).rejects.toBe(denied);
  }
);

it('keeps the contacts without-stage column independent from configured stages', async () => {
  vi.mocked(apiRequest).mockResolvedValue({
    results: [{ id: 'unassigned', first_name: 'Example' }],
    count: 1
  });
  const parent = vi.fn(() => {
    throw new Error('No parent needed');
  });
  const result = await contacts(
    /** @type {any} */ ({
      cookies: {},
      depends: vi.fn(),
      parent,
      url: new URL('https://crm.example.com/contacts?view=pipeline&stage=UNASSIGNED')
    })
  );
  expect(parent).not.toHaveBeenCalled();
  expect(result).toMatchObject({ board: [{ value: 'UNASSIGNED', label: 'No stage', count: 1 }] });
});
