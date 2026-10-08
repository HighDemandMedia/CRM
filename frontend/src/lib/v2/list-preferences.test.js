import { describe, it, expect } from 'vitest';
import {
  columnWidths,
  preferenceKey,
  readPreference,
  writePreference,
  viewPreferences
} from './list-preferences.js';
import { validColumns } from './list-columns.js';

describe('durable list preferences', () => {
  it('restores a saved column order after a new reader opens the list', () => {
    const data = new Map();
    const storage = {
      getItem: (key) => data.get(key),
      setItem: (key, value) => data.set(key, value)
    };
    const key = preferenceKey('columns', 'org.user.Contact');
    writePreference(storage, key, ['email', 'name']);
    expect(
      validColumns(readPreference(storage, key, null), [{ key: 'name' }, { key: 'email' }])
    ).toEqual(['email', 'name']);
  });
  it('separates users, organizations and objects', () => {
    const keys = ['a.u.Contact', 'a.v.Contact', 'b.u.Contact', 'a.u.Company'].map((scope) =>
      preferenceKey('widths', scope)
    );
    expect(new Set(keys).size).toBe(4);
  });
  it('ignores removed columns without losing the order of existing ones', () => {
    expect(
      validColumns(['removed', 'email', 'email', 'name'], [{ key: 'name' }, { key: 'email' }])
    ).toEqual(['email', 'name']);
  });
  it('ignores damaged or disabled storage', () => {
    expect(readPreference({ getItem: () => '{' }, 'key', null)).toBeNull();
    expect(() =>
      writePreference(
        {
          setItem: () => {
            throw new Error('blocked');
          }
        },
        'key',
        {}
      )
    ).not.toThrow();
  });
  it('bounds widths and rejects corrupt values', () => {
    expect(columnWidths({ name: 200, email: -1, phone: '100', description: 1e9 })).toEqual({
      name: 200
    });
    expect(columnWidths(['invalid'])).toEqual({});
  });
  it('remembers sorting without persisting view mode, searches or pagination', () => {
    expect(
      viewPreferences(
        new URLSearchParams('view=pipeline&sort=name&direction=desc&search=private&offset=50')
      )
    ).toEqual({ sort: 'name', direction: 'desc' });
    expect(viewPreferences(new URLSearchParams('view=unknown&direction=wrong'))).toEqual({});
  });
  it('does not restore pipeline mode saved by an older version', () => {
    const stored = JSON.stringify({ view: 'pipeline', sort: 'name', direction: 'asc' });
    const saved = readPreference({ getItem: () => stored }, 'key', {});
    expect(viewPreferences(new URLSearchParams(saved))).toEqual({
      sort: 'name',
      direction: 'asc'
    });
    expect(viewPreferences(new URLSearchParams({ view: 'pipeline' }))).toEqual({});
  });
});
