import { describe, expect, it } from 'vitest';
import { withoutBase } from './paths.js';
import { paginationHref } from '../v2/pagination.js';

describe('browser paths resolved against an application base', () => {
  it.each([
    ['/contacts?view=pipeline#top', '', '/contacts?view=pipeline#top'],
    [
      '/crm/contacts?owner=one%2Btwo&offset=25#record',
      '/crm',
      '/contacts?owner=one%2Btwo&offset=25#record'
    ],
    ['/crm', '/crm', '/'],
    ['/crm?view=list', '/crm', '/?view=list'],
    ['/crm#today', '/crm', '/#today'],
    ['/crm-tools/contacts', '/crm', '/crm-tools/contacts'],
    ['/contacts', '/crm', '/contacts']
  ])('normalizes %s without duplicating or corrupting the base', (path, base, expected) => {
    expect(withoutBase(path, base)).toBe(expected);
  });

  it('preserves filters and applies the base exactly once when paginating', () => {
    const base = '/crm';
    const current = new URL(
      'https://crm.example.com/crm/contacts?stage=QUALIFIED&sort=name&offset=25'
    );
    const next = paginationHref(current, { offset: 50, pageSize: undefined });
    const resolved = base + withoutBase(next, base);
    expect(resolved).toBe('/crm/contacts?stage=QUALIFIED&sort=name&offset=50');
    const resized = paginationHref(current, { pageSize: 10, offset: 0 });
    expect(base + withoutBase(resized, base)).toBe(
      '/crm/contacts?stage=QUALIFIED&sort=name&page_size=10'
    );
  });
});
