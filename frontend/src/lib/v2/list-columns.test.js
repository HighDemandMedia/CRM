import { describe, expect, it } from 'vitest';
import { listColumns, columnValue, validColumns } from './list-columns.js';
const config = {
  system: [
    { key: 'id', label: 'Record ID' },
    { key: 'first_name', label: 'Name' },
    { key: 'email', label: 'Email' }
  ],
  custom: [
    {
      key: 'segment',
      label: 'Segment',
      field_type: 'dropdown',
      options: [{ value: 'vip', label: 'VIP' }]
    }
  ],
  order: ['first_name', 'custom_fields.segment', 'email', 'id']
};
describe('organization list columns', () => {
  it('includes system and custom properties in the configured order, without duplicate aliases', () => {
    const columns = listColumns('Contact', config, [['name', 'Name']]);
    expect(columns.map((c) => c.key)).toEqual(['name', 'custom_fields.segment', 'email', 'id']);
    expect(validColumns(null, columns)).toEqual(['name', 'email']);
  });
  it('removes unavailable saved columns and retains the user order', () => {
    const columns = listColumns('Contact', config);
    expect(validColumns(['email', 'deleted', 'name', 'email'], columns)).toEqual(['email', 'name']);
    expect(validColumns(['deleted'], columns)).toEqual(['name', 'email']);
    expect(validColumns({}, columns)).toEqual(['name', 'email']);
  });
  it('hides notes and record ID by default but retains explicit selections for every object', () => {
    for (const target of ['Contact', 'Account', 'Opportunity', 'Task', 'Case']) {
      const columns = listColumns(target, {
        system: [
          { key: 'name', label: 'Name' },
          { key: 'description', label: 'Notes' },
          { key: 'id', label: 'Record ID' }
        ],
        custom: []
      });
      expect(validColumns(null, columns)).toEqual(['name']);
      expect(validColumns(['description', 'id', 'name'], columns)).toEqual([
        'description',
        'id',
        'name'
      ]);
      expect(columns.map((column) => column.key)).toContain('description');
      expect(columns.map((column) => column.key)).toContain('id');
    }
  });
  it('formats custom values, relations, zero and false without displaying object internals', () => {
    const columns = listColumns('Contact', config);
    const row = {
      custom_fields: { segment: 'vip' },
      zero: 0,
      checked: false,
      contacts: [{ name: 'Ana' }, { first_name: 'Luis', last_name: 'Perez' }],
      hidden: { id: 'private' }
    };
    expect(columnValue(row, 'custom_fields.segment', columns)).toBe('VIP');
    expect(columnValue(row, 'zero', columns)).toBe('0');
    expect(columnValue(row, 'checked', columns)).toBe('No');
    expect(columnValue(row, 'contacts', columns)).toBe('Ana, Luis Perez');
    expect(columnValue(row, 'hidden', columns)).toBe('—');
  });
  it('does not share custom property catalogs between organizations', () => {
    expect(
      validColumns(
        ['custom_fields.segment'],
        listColumns('Contact', { system: config.system, custom: [] })
      )
    ).toEqual(['name', 'email']);
  });
});
