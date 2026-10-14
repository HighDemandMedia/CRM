import { describe, expect, it } from 'vitest';
import { legalFormValues, legalLinks } from './legal.js';

describe('legal documents and explicit acceptance', () => {
  it('links to the corresponding public language without accepting user-provided hosts', () => {
    expect(legalLinks('es-US').terms).toBe('https://highdemandmedia.com/crm-terms-es.html');
    expect(legalLinks('en-US').privacy).toBe('https://highdemandmedia.com/crm-privacy.html');
    expect(legalLinks('https://evil.example').privacy).toBe(
      'https://highdemandmedia.com/crm-privacy.html'
    );
    expect(legalLinks('es').dpa).toBe('/legal/dpa?lang=es');
    expect(legalLinks('en').dpa).toBe('/legal/dpa?lang=en');
  });
  it('never invents acceptance for missing or unchecked fields', () => {
    expect(legalFormValues(new FormData())).toEqual({
      legal_version: '',
      legal_locale: '',
      accept_terms: false,
      organization_authority: false
    });
  });
  it('forwards the version that was displayed, not an implicitly accepted latest version', () => {
    const form = new FormData();
    form.set('legal_version', '2026-10-12');
    form.set('legal_locale', 'es');
    form.set('accept_terms', 'on');
    expect(legalFormValues(form)).toEqual({
      legal_version: '2026-10-12',
      legal_locale: 'es',
      accept_terms: true,
      organization_authority: false
    });
  });
});
