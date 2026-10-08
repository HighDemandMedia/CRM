import { it, expect, vi, beforeEach } from 'vitest';
vi.mock('$lib/server/v2/contacts.js', () => ({ listContacts: vi.fn(), updateContact: vi.fn() }));
vi.mock('$lib/server/v2/contact-query.js', () => ({
  contactQuery: (url) => new URLSearchParams(url.searchParams)
}));
vi.mock('$lib/server/v2/org-people.js', () => ({
  getOrgPeopleAndTeams: vi.fn().mockResolvedValue({ people: [] }),
  resolveMe: vi.fn()
}));
vi.mock('$lib/server/v2/tags.js', () => ({ getTags: vi.fn().mockResolvedValue({ tags: [] }) }));
import { listContacts } from '$lib/server/v2/contacts.js';
import { load } from './+page.server.js';
/** @returns {any} */
const event = (query) => ({
  cookies: {},
  locals: {},
  url: new URL('http://localhost/contacts?' + query),
  parent: async () => ({ pipelineConfig: {} })
});
beforeEach(() => {
  vi.mocked(listContacts)
    .mockReset()
    .mockResolvedValue(/** @type {any} */ ({ results: [], totals: { count: 120 }, stages: [] }));
});
it.each([
  ['', 25],
  ['page_size=10', 10],
  ['page_size=50', 50],
  ['page_size=100', 100],
  ['page_size=999999', 25],
  ['page_size=-1', 25],
  ['page_size=invalid', 25]
])('bounds contacts pages: %s', async (query, size) => {
  const data = /** @type {any} */ (await load(event(query)));
  expect(data.pageSize).toBe(size);
  expect(vi.mocked(listContacts).mock.calls[0][1].get('limit')).toBe(String(size));
});
it('preserves filters and offset for the next page', async () => {
  await load(event('search=Ana&stage=LEAD&offset=50&page_size=25'));
  const p = vi.mocked(listContacts).mock.calls[0][1];
  expect(p.get('offset')).toBe('50');
  expect(p.get('search')).toBe('Ana');
  expect(p.get('stage')).toBe('LEAD');
});
it('redirects an out-of-range page to the last page preserving filters', async () => {
  await expect(load(event('offset=200&page_size=25&search=Ana'))).rejects.toMatchObject({
    status: 303,
    location: '/contacts?offset=100&page_size=25&search=Ana'
  });
});
it('returns to the first page when the filtered list is now empty', async () => {
  vi.mocked(listContacts).mockResolvedValueOnce(
    /** @type {any} */ ({ results: [], totals: { count: 0 }, stages: [] })
  );
  await expect(load(event('offset=25'))).rejects.toMatchObject({
    status: 303,
    location: '/contacts?offset=0'
  });
});
