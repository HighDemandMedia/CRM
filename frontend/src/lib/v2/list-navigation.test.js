import { expect, it } from 'vitest';
import { savedListLinks } from './list-navigation.js';
import { preferenceKey } from './list-preferences.js';

const entries = new Map();
const storage = { getItem: (key) => entries.get(key) ?? null };
it('resolves sorting before navigation without restoring filters or pipeline mode', () => {
  entries.set(
    preferenceKey('view', 'org.me.Contact'),
    JSON.stringify({ sort: 'first_name', direction: 'desc', view: 'pipeline', owner: 'other' })
  );
  expect(savedListLinks(storage, 'org', 'me', new URL('http://localhost/tasks'))['/contacts']).toBe(
    '/contacts?sort=first_name&direction=desc'
  );
  expect(savedListLinks(storage, 'other-org', 'me', null)['/contacts']).toBe('/contacts');
  expect(savedListLinks(storage, 'org', 'other-user', null)['/contacts']).toBe('/contacts');
});
it('uses current sorting before the persistence effect finishes', () => {
  expect(
    savedListLinks(
      storage,
      'org',
      'me',
      new URL('http://localhost/contacts?sort=email&direction=asc')
    )['/contacts']
  ).toBe('/contacts?sort=email&direction=asc');
});
it('tolerates disabled storage, malformed data, and absent identity', () => {
  expect(savedListLinks(null, 'org', 'me', null)['/contacts']).toBe('/contacts');
  expect(savedListLinks(storage, '', 'me', null)).toEqual({});
  entries.set(preferenceKey('view', 'org.me.Contact'), 'invalid-json');
  expect(savedListLinks(storage, 'org', 'me', null)['/contacts']).toBe('/contacts');
});
