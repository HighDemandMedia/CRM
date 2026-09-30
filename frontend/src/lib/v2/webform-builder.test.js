import { describe, it, expect } from 'vitest';
import { suggestProperty, mappingRows, buttonTextColor } from './webform-builder.js';
describe('HTML field suggestions', () => {
  it('recognizes common English and Spanish field names and native input types', () => {
    for (const [name, property] of [
      ['your-email', 'email'],
      ['nombre', 'first_name'],
      ['apellido', 'last_name'],
      ['company', 'organization'],
      ['mensaje', 'description'],
      ['telefono', 'phone']
    ]) {
      expect(suggestProperty(name)).toBe(property);
    }
    expect(suggestProperty('contact-method', 'email')).toBe('email');
    expect(suggestProperty('budget')).toBe('');
  });
  it('requires an explicit choice for ambiguous duplicate targets', () => {
    const result = mappingRows([
      { name: 'email', property: 'email' },
      { name: 'confirm-email', property: 'email' },
      { name: 'budget', property: '' }
    ]);
    expect(result.map((r) => r.property)).toEqual(['email', '', '']);
  });
  it('selects readable button text for dark and light backgrounds', () => {
    expect(buttonTextColor('#ffffff')).toBe('#000000');
    expect(buttonTextColor('#000000')).toBe('#ffffff');
    expect(buttonTextColor('#ffff00')).toBe('#000000');
  });
});
