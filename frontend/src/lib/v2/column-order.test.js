import { describe, expect, it } from 'vitest';
import { insertColumn } from './column-order.js';
import { validColumns } from './list-columns.js';

describe('list column order', () => {
  const keys = ['name', 'status', 'custom_fields.region', 'assigned_to'];
  it('moves in either direction, including the first and last gaps', () => {
    expect(insertColumn(keys, 'name', 4)).toEqual([
      'status',
      'custom_fields.region',
      'assigned_to',
      'name'
    ]);
    expect(insertColumn(keys, 'assigned_to', 0)).toEqual([
      'assigned_to',
      'name',
      'status',
      'custom_fields.region'
    ]);
    expect(insertColumn(keys, 'status', 3)).toEqual([
      'name',
      'custom_fields.region',
      'status',
      'assigned_to'
    ]);
    expect(keys).toEqual(['name', 'status', 'custom_fields.region', 'assigned_to']);
  });
  it('leaves adjacent gaps, unavailable columns and out-of-bounds keyboard moves unchanged', () => {
    for (const gap of [1, 2, -1, 5]) expect(insertColumn(keys, 'status', gap)).toEqual(keys);
    expect(insertColumn(keys, 'missing', 0)).toEqual(keys);
    expect(insertColumn([], 'name', 0)).toEqual([]);
  });
  it('retains reordered custom fields through saved preference validation', () => {
    const saved = JSON.parse(JSON.stringify(insertColumn(keys, 'custom_fields.region', 0)));
    expect(
      validColumns(
        saved,
        keys.map((key) => ({ key }))
      )
    ).toEqual(saved);
    expect(
      validColumns(
        saved,
        keys.filter((key) => key !== 'status').map((key) => ({ key }))
      )
    ).toEqual(['custom_fields.region', 'name', 'assigned_to']);
  });
});
