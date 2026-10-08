import { describe, it, expect, vi, beforeEach } from 'vitest';
import { listPagination, checkListPage } from './pagination.js';
import { paginationHref } from '$lib/v2/pagination.js';
import { taskQuery, ticketQuery } from './queue-query.js';

vi.mock('./accounts.js', () => ({ listAccounts: vi.fn(), updateAccount: vi.fn() }));
vi.mock('./deals.js', () => ({ listDeals: vi.fn(), moveDeal: vi.fn() }));
vi.mock('./tasks.js', async (original) => ({ ...(await original()), listTasks: vi.fn() }));
vi.mock('./tickets.js', async (original) => ({ ...(await original()), listTickets: vi.fn() }));
vi.mock('./org-people.js', () => ({
  getOrgPeopleAndTeams: vi.fn().mockResolvedValue({ people: [] }),
  resolveMe: vi.fn()
}));
vi.mock('./tags.js', () => ({ getTags: vi.fn().mockResolvedValue({ tags: [] }) }));
import { listAccounts } from './accounts.js';
import { listDeals } from './deals.js';
import { listTasks } from './tasks.js';
import { listTickets } from './tickets.js';
import { load as companies } from '../../../routes/(app)/accounts/+page.server.js';
import { load as deals } from '../../../routes/(app)/pipeline/+page.server.js';
import { load as tasks } from '../../../routes/(app)/tasks/+page.server.js';
import { load as tickets } from '../../../routes/(app)/tickets/+page.server.js';

/** @returns {any} */
const event = (path, query) => ({
  cookies: {},
  locals: {},
  url: new URL(`http://localhost/${path}?${query}`),
  parent: async () => ({ pipelineConfig: {} })
});
const rowResponse = () =>
  /** @type {any} */ ({ results: [], totals: { count: 125 }, owners: [], stages: [] });
beforeEach(() => {
  for (const list of [listAccounts, listDeals, listTasks, listTickets])
    vi.mocked(list).mockReset().mockResolvedValue(rowResponse());
});

describe.each([
  ['accounts', companies, listAccounts],
  ['pipeline', deals, listDeals],
  ['tasks', tasks, listTasks],
  ['tickets', tickets, listTickets]
])('%s paginated list', (path, load, list) => {
  it.each([
    ['', 25],
    ['page_size=10', 10],
    ['page_size=50', 50],
    ['page_size=100', 100],
    ['page_size=100000', 25]
  ])('limits the server request: %s', async (query, size) => {
    const data = /** @type {any} */ (await load(event(path, query)));
    expect(data.pageSize).toBe(size);
    expect(vi.mocked(list).mock.calls[0][1].get('limit')).toBe(String(size));
  });
  it('loads later pages while retaining search', async () => {
    await load(event(path, 'offset=50&page_size=25&search=Ana&q=Ana'));
    const query = vi.mocked(list).mock.calls[0][1];
    expect(query.get('offset')).toBe('50');
    expect(query.get('search')).toBe('Ana');
  });
  it('recovers after the last page is deleted', async () => {
    vi.mocked(list).mockResolvedValueOnce({ ...rowResponse(), totals: { count: 26 } });
    await expect(load(event(path, 'offset=50&page_size=25&search=Ana'))).rejects.toMatchObject({
      status: 303,
      location: `/${path}?offset=25&page_size=25&search=Ana`
    });
  });
  it('recovers when a filtered list becomes empty', async () => {
    vi.mocked(list).mockResolvedValueOnce({ ...rowResponse(), totals: { count: 0 } });
    await expect(load(event(path, 'offset=25'))).rejects.toMatchObject({
      status: 303,
      location: `/${path}?offset=0`
    });
  });
});
it('bounds and aligns offsets, and isolates per-stage boards', () => {
  expect(listPagination(new URL('http://localhost/?offset=-50&page_size=-1'))).toEqual({
    offset: 0,
    pageSize: 25
  });
  expect(listPagination(new URL('http://localhost/?offset=37&page_size=25'))).toEqual({
    offset: 25,
    pageSize: 25
  });
  expect(listPagination(new URL('http://localhost/?offset=9999999999'))).toEqual({
    offset: 10000000,
    pageSize: 25
  });
  expect(listPagination(new URL('http://localhost/?offset=100&page_size=100'), false)).toEqual({
    offset: 0,
    pageSize: 25
  });
  expect(() =>
    checkListPage(new URL('http://localhost/'), { offset: 0, pageSize: 25 }, 0)
  ).not.toThrow();
});
it('keeps filters and sort on navigation, and resets offset on size change', () => {
  const url = new URL(
    'http://localhost/tasks?q=Ana&status=New&sort=name&direction=desc&page_size=25&offset=50'
  );
  const next = new URL(paginationHref(url, { offset: 75, pageSize: undefined }), url);
  expect(next.searchParams.get('q')).toBe('Ana');
  expect(next.searchParams.get('sort')).toBe('name');
  expect(next.searchParams.get('direction')).toBe('desc');
  expect(next.searchParams.get('offset')).toBe('75');
  const resized = new URL(paginationHref(url, { pageSize: 100, offset: 0 }), url);
  expect(resized.searchParams.has('offset')).toBe(false);
  expect(resized.searchParams.get('status')).toBe('New');
  expect(resized.searchParams.get('page_size')).toBe('100');
});
it('filters open tasks before slicing without overriding an explicit status', () => {
  expect(taskQuery(new URL('http://localhost/tasks?all=0')).get('exclude_completed')).toBe('true');
  expect(
    taskQuery(new URL('http://localhost/tasks?all=0&status=Completed')).has('exclude_completed')
  ).toBe(false);
  expect(taskQuery(new URL('http://localhost/tasks?all=1')).has('exclude_completed')).toBe(false);
});
it('only forwards supported ticket sorting to the API', () => {
  expect(
    ticketQuery(new URL('http://localhost/tickets?sort=ticket_code&direction=desc'), {}).get(
      'ordering'
    )
  ).toBe('-ticket_number');
  expect(ticketQuery(new URL('http://localhost/tickets?sort=due_at'), {}).get('ordering')).toBe(
    'due_at'
  );
  expect(ticketQuery(new URL('http://localhost/tickets?sort=secret'), {}).has('ordering')).toBe(
    false
  );
});
