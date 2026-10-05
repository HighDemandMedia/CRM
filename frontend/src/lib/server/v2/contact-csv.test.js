vi.mock('$lib/api-helpers.js', () => ({
  apiRequest: vi.fn().mockResolvedValue({ property_layout: {} })
}));
import { expect, it, vi } from 'vitest';
vi.mock('./contacts.js', () => ({
  listContacts: vi.fn(),
  FILTER_FIELDS: ['assigned_to', 'tags', 'city']
}));
import { listContacts } from './contacts.js';
import { csvCell, exportContacts } from './contact-csv.js';
it('quotes CSV text and neutralizes formulas', () => {
  expect(csvCell('a,"b"\nc')).toBe('"a,""b""\nc"');
  expect(csvCell('=1+1')).toBe('"\'=1+1"');
  expect(csvCell(' +SUM(A1)')).toBe('"\' +SUM(A1)"');
});
it('exports every filtered page with selected columns in order', async () => {
  vi.mocked(listContacts)
    .mockResolvedValueOnce(
      /** @type {any} */ ({ results: [{ name: 'First', phone: '123' }], totals: { count: 2 } })
    )
    .mockResolvedValueOnce(
      /** @type {any} */ ({ results: [{ name: 'Second', phone: '456' }], totals: { count: 2 } })
    );
  const event = {
    cookies: {},
    url: new URL(
      'http://localhost/contacts/export?search=First&stage=LEAD&created_at__gte=2026-09-01&last_activity_at__lte=2026-09-10&sort=name&direction=asc&columns=phone,name'
    )
  };
  const csv = await exportContacts(event);
  expect(csv).toBe('\uFEFF"Phone","Name"\r\n"123","First"\r\n"456","Second"\r\n');
  const query = vi.mocked(listContacts).mock.calls[0][1];
  expect(query.get('search')).toBe('First');
  expect(query.get('stage')).toBe('LEAD');
  expect(query.get('last_activity_at__lte')).toBe('2026-09-10');
  expect(query.get('created_at__gte')).toBe('2026-09-01');
  expect(query.get('sort')).toBe('name');
  expect(listContacts).toHaveBeenCalledTimes(2);
});

it('exports organization custom columns and ignores unknown keys', async () => {
  const { apiRequest } = await import('$lib/api-helpers.js');
  vi.mocked(apiRequest).mockResolvedValueOnce({
    property_layout: {
      Contact: {
        system: [{ key: 'first_name', label: 'Name' }],
        custom: [
          {
            key: 'segment',
            label: 'Segment',
            field_type: 'dropdown',
            options: [{ value: 'vip', label: 'VIP' }]
          }
        ]
      }
    }
  });
  vi.mocked(listContacts).mockResolvedValueOnce(
    /** @type {any} */ ({
      results: [{ name: 'Ana', custom_fields: { segment: 'vip', private: 'not in catalog' } }],
      totals: { count: 1 }
    })
  );
  const csv = await exportContacts({
    cookies: {},
    url: new URL(
      'http://localhost/contacts/export?columns=name,custom_fields.segment,custom_fields.private'
    )
  });
  expect(csv).toBe('\uFEFF"Name","Segment"\r\n"Ana","VIP"\r\n');
});
