vi.mock('$lib/api-helpers.js', () => ({
  apiRequest: vi.fn().mockResolvedValue({ property_layout: {} })
}));
import { expect, it, vi } from 'vitest';
vi.mock('./accounts.js', () => ({
  listAccounts: vi.fn(),
  FILTER_FIELDS: ['assigned_to', 'tags', 'city']
}));
import { listAccounts } from './accounts.js';
import { csvCell, exportCompanies } from './company-csv.js';
it('quotes CSV text and neutralizes formulas', () => {
  expect(csvCell('a,"b"\nc')).toBe('"a,""b""\nc"');
  expect(csvCell('=1+1')).toBe('"\'=1+1"');
  expect(csvCell(' +SUM(A1)')).toBe('"\' +SUM(A1)"');
});
it('exports every filtered page with selected columns in order', async () => {
  vi.mocked(listAccounts)
    .mockResolvedValueOnce(
      /** @type {any} */ ({ results: [{ name: 'First', website: '123' }], totals: { count: 2 } })
    )
    .mockResolvedValueOnce(
      /** @type {any} */ ({ results: [{ name: 'Second', website: '456' }], totals: { count: 2 } })
    );
  const event = {
    cookies: {},
    url: new URL(
      'http://localhost/contacts/export?search=First&source=META&created_at__gte=2026-09-01&updated_at__lte=2026-09-10&sort=name&direction=asc&columns=website,name'
    )
  };
  const csv = await exportCompanies(event);
  expect(csv).toBe('\uFEFF"Domain","Name"\r\n"123","First"\r\n"456","Second"\r\n');
  const query = vi.mocked(listAccounts).mock.calls[0][1];
  expect(query.get('search')).toBe('First');
  expect(query.get('source')).toBe('META');
  expect(query.get('updated_at__lte')).toBe('2026-09-10');
  expect(query.get('created_at__gte')).toBe('2026-09-01');
  expect(query.get('sort')).toBe('name');
  expect(listAccounts).toHaveBeenCalledTimes(2);
});
