import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { COUNTRIES, countryOptions, getCountryName } from './countries.js';
import { matchesChoice } from '$lib/v2/choice-search.js';

describe('international country catalog', () => {
  it('offers all 249 current ISO countries/territories and keeps stored AN readable', () => {
    const options = countryOptions();
    expect(options).toHaveLength(249);
    expect(new Set(options.map((o) => o.value)).size).toBe(249);
    expect(options.every((o) => /^[A-Z]{2}$/.test(o.value))).toBe(true);
    expect(options.some((o) => o.value === 'AN')).toBe(false);
    expect(countryOptions('AN').some((o) => o.value === 'AN')).toBe(true);
    expect(getCountryName('AN')).toBe('Netherlands Antilles');
    expect(['BQ', 'CW', 'SX', 'SS'].every((code) => options.some((o) => o.value === code))).toBe(
      true
    );
  });
  it('matches the countries accepted by the backend', () => {
    const backend = readFileSync(
      new URL('../../../../backend/common/utils.py', import.meta.url),
      'utf8'
    );
    const section = backend.split('COUNTRIES = (')[1].split('\n)')[0];
    const codes = [...section.matchAll(/\("([A-Z]{2})",/g)].map((match) => match[1]);
    expect(COUNTRIES.map((c) => c.code).sort()).toEqual(codes.sort());
  });
  it('uses localized labels, US first, then alphabetical order', () => {
    const options = countryOptions('', 'es');
    expect(options[0]).toMatchObject({ value: 'US', label: 'Estados Unidos' });
    expect(options.find((o) => o.value === 'DE').label).toBe('Alemania');
    const labels = options.slice(1).map((o) => o.label);
    expect(labels).toEqual([...labels].sort((a, b) => a.localeCompare(b, 'es')));
  });
  it.each([
    ['es', 'Germany', 'DE'],
    ['en', 'espana', 'ES'],
    ['en', 'CW', 'CW'],
    ['es', 'Curaçao', 'CW']
  ])('finds %s options by %s', (locale, query, code) => {
    expect(
      countryOptions('', locale)
        .filter((o) => matchesChoice(o, query))
        .map((o) => o.value)
    ).toContain(code);
  });
  it('leaves unknown stored country codes readable', () => {
    expect(getCountryName('ZZ')).toBe('ZZ');
  });
});
