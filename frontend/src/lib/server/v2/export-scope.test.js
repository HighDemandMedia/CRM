import { describe, it, expect, vi } from 'vitest';
import { exportQueryURL, exportRows, postExport } from './export-scope.js';
import { exportContacts } from './contact-csv.js';
vi.mock('$lib/api-helpers.js', () => ({
  apiRequest: vi.fn().mockResolvedValue({ property_layout: {} })
}));
vi.mock('./contacts.js', () => ({ listContacts: vi.fn(), FILTER_FIELDS: ['assigned_to', 'tags'] }));
import { listContacts } from './contacts.js';
const id1 = '11111111-1111-4111-8111-111111111111';
const id2 = '22222222-2222-4222-8222-222222222222';
async function collect(event, list) {
  const rows = [];
  for await (const row of exportRows(event, new URLSearchParams('search=Ana'), list))
    rows.push(row);
  return rows;
}
describe('export scopes', () => {
  it('defaults to filtered and rejects invalid scopes', () => {
    expect(
      exportQueryURL(new URL('http://localhost/export?search=Ana')).searchParams.get('search')
    ).toBe('Ana');
    expect(() => exportQueryURL(new URL('http://localhost/export?scope=unknown'))).toThrow();
  });
  it('all removes filters while retaining sort and includes inactive contacts', async () => {
    vi.mocked(listContacts).mockResolvedValueOnce(
      /** @type {any} */ ({
        results: [{ name: 'Ana' }],
        totals: { count: 1 }
      })
    );
    await exportContacts({
      cookies: {},
      url: new URL(
        'http://localhost/export?scope=all&search=Ana&stage=LEAD&columns=name&sort=name&direction=desc'
      )
    });
    const query = vi.mocked(listContacts).mock.calls.at(-1)[1];
    expect(query.get('search')).toBeNull();
    expect(query.get('stage')).toBeNull();
    expect(query.get('is_active')).toBeNull();
    expect(query.get('sort')).toBe('name');
    expect(query.get('permission_action')).toBe('export');
  });
  it('page only includes authorized IDs and preserves their displayed order', async () => {
    const list = vi
      .fn()
      .mockResolvedValueOnce({ results: [{ id: id1 }, { id: 'other' }], totals: { count: 3 } })
      .mockResolvedValueOnce({ results: [{ id: id2 }], totals: { count: 3 } });
    const rows = await collect(
      { url: new URL('http://localhost/export?scope=page'), exportIds: [id2, 'inaccessible', id1] },
      list
    );
    expect(rows.map((r) => r.id)).toEqual([id2, id1]);
    expect(list.mock.calls.every((call) => call[1].get('permission_action') === 'export')).toBe(
      true
    );
  });
  it('does not turn an empty page into an export of everything', async () => {
    const list = vi.fn();
    expect(
      await collect({ url: new URL('http://localhost/export?scope=page'), exportIds: [] }, list)
    ).toEqual([]);
    expect(list).not.toHaveBeenCalled();
  });
  it('fails on missing IDs or canceled requests', async () => {
    await expect(
      collect({ url: new URL('http://localhost/export?scope=page') }, vi.fn())
    ).rejects.toThrow();
    await expect(
      collect(
        { url: new URL('http://localhost/export'), request: { signal: { aborted: true } } },
        vi.fn()
      )
    ).rejects.toThrow('Export canceled');
  });
  it('validates supplied IDs before the export handler', async () => {
    const body = new FormData();
    body.append('ids', 'not-a-uuid');
    const handler = vi.fn();
    await expect(
      postExport({ request: new Request('http://localhost', { method: 'POST', body }) }, handler)
    ).rejects.toThrow();
    expect(handler).not.toHaveBeenCalled();
  });
});
