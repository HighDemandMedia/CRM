import { describe, expect, it } from 'vitest';
import { normalizeLocale, translate, intlLocale } from './messages.js';
import es from './es.json';
import { money, shortDate, relativeDays } from '$lib/v2/format.js';

describe('account language', () => {
  it('supports only English and Spanish', () => {
    expect(normalizeLocale('es')).toBe('es');
    for (const input of [undefined, '', 'fr', '<script>', 'ES'])
      expect(normalizeLocale(input)).toBe('en');
  });
  it('keeps simultaneous readers independent', () => {
    expect(translate('es', 'Contacts')).toBe('Contactos');
    expect(translate('en', 'Contacts')).toBe('Contacts');
    expect(translate('es', 'Contacts')).toBe('Contactos');
  });
  it('does not rewrite unknown customer content or interpolation values', () => {
    expect(translate('es', 'Acme <b>North</b>')).toBe('Acme <b>North</b>');
    expect(translate('es', 'Record {name}', { name: 'Contacts' })).toBe('Record Contacts');
  });
  it('preserves interpolation keys in the Spanish catalog', () => {
    for (const [source, translated] of Object.entries(es)) {
      expect(translated.trim().length, source).toBeGreaterThan(0);
      expect([...translated.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort(), source).toEqual(
        [...source.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()
      );
    }
  });
  it('formats Spanish dates and relative time without changing dates or currency', () => {
    expect(intlLocale('es')).toBe('es-US');
    expect(shortDate('2026-10-05', new Date('2026-10-06T12:00:00'), 'es-US')).toContain('oct');
    expect(relativeDays('2026-10-05', new Date('2026-10-06T12:00:00'), 'es-US')).toBe('ayer');
    expect(money(1200, 'EUR', 'es-US')).toBe(
      new Intl.NumberFormat('es-US', {
        style: 'currency',
        currency: 'EUR',
        maximumFractionDigits: 0
      }).format(1200)
    );
  });
});
