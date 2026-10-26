import { describe, it, expect } from 'vitest';
import {
  editableProperty,
  propertyRawValue,
  propertyDraft,
  propertyValue,
  samePropertyValue
} from './inline-property.js';
const schema = {
  fields: [
    { key: 'city', field_type: 'text' },
    { key: 'stage', field_type: 'dropdown' },
    { key: 'assigned_to', relation: 'Profile' },
    { key: 'appointment_at' }
  ]
};
/** @param {string | boolean} edit @param {string | boolean} reassign */
const permissions = (edit = 'own', reassign = 'own') => ({
  rules: { contacts: { edit, reassign } }
});
describe('inline record property contracts', () => {
  it('keeps read-only and unauthorized fields uneditable', () => {
    expect(editableProperty({ key: 'city' }, 'Contact', schema, permissions(false), {})).toBeNull();
    expect(
      editableProperty({ key: 'appointment_at' }, 'Contact', schema, permissions(), {})
    ).toBeNull();
    expect(
      editableProperty({ key: 'created_by' }, 'Contact', schema, permissions(), {})
    ).toBeNull();
    expect(
      editableProperty(
        { key: 'city', definition: { key: 'custom_city' } },
        'Contact',
        schema,
        permissions(false),
        {}
      )
    ).toBeNull();
  });
  it('hides reassignment for members and preserves multiple owners for managers', () => {
    expect(
      editableProperty({ key: 'assigned_to' }, 'Contact', schema, permissions(), {})
    ).toBeNull();
    const field = editableProperty(
      { key: 'assigned_to' },
      'Contact',
      schema,
      permissions('team', 'team'),
      {}
    );
    expect(field.multiple).toBe(true);
    expect(propertyRawValue({ assigned_to: ['a', 'b'] }, field)).toEqual(['a', 'b']);
  });
  it('uses configured pipeline choices and raw values rather than translated labels', () => {
    expect(
      editableProperty({ key: 'stage' }, 'Contact', schema, permissions(), {
        Contact: { stages: [{ key: 'LEAD', label: 'Nuevo' }] }
      }).options[0]
    ).toMatchObject({ value: 'LEAD', label: 'Nuevo' });
    expect(
      propertyRawValue({ industry: 'Home Services', industry_value: 'HOME' }, { key: 'industry' })
    ).toBe('HOME');
  });
  it('does not mutate original multi-select or page values during editing', () => {
    const source = ['a', 'b'];
    const draft = propertyDraft(source, { multiple: true });
    draft.pop();
    expect(source).toEqual(['a', 'b']);
    const pages = [{ name: 'Home', url: 'https://example.com' }];
    propertyDraft(pages, { key: 'pages' })[0].name = 'Changed';
    expect(pages[0].name).toBe('Home');
  });
  it('preserves false and zero, parses lists, and detects unchanged selections', () => {
    expect(
      propertyValue(propertyDraft(false, { field_type: 'checkbox' }), { field_type: 'checkbox' })
    ).toBe(false);
    expect(propertyDraft(0, {})).toBe(0);
    expect(propertyValue('[1,2]', { field_type: 'list' })).toEqual([1, 2]);
    expect(() => propertyValue('broken', { field_type: 'list' })).toThrow();
    expect(samePropertyValue(['a', 'b'], ['b', 'a'])).toBe(true);
    expect(samePropertyValue('', null)).toBe(true);
    expect(samePropertyValue('Miami', 'Orlando')).toBe(false);
  });
});
