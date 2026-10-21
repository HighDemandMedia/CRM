import { expect, it } from 'vitest';
import { propertyPlaceholder, propertyValueError } from './custom-field-input.js';
import { translate } from '$lib/i18n/messages.js';

it.each(['phone', 'email', 'url'])('provides a valid format example for %s', (type) => {
  const value = propertyPlaceholder({ key: type, field_type: type });
  expect(value).not.toBe('');
  expect(propertyValueError(type, value)).toBe('');
});
it('uses record-specific identity examples', () => {
  expect(propertyPlaceholder({ key: 'name' }, 'Account')).toBe('e.g. Acme Inc.');
  expect(propertyPlaceholder({ key: 'name' }, 'Opportunity')).toBe('e.g. Website redesign');
});
it('does not interpret custom field names as built-in properties', () => {
  expect(propertyPlaceholder({ key: 'state', custom: true, field_type: 'text' })).toBe(
    'Enter a value'
  );
});
it('localizes authored examples without changing date controls', () => {
  expect(translate('es', propertyPlaceholder({ key: 'state' }))).toBe('p. ej., Florida');
  expect(propertyPlaceholder({ field_type: 'date' })).toBe('');
});
it('gives list fields a parseable example', () => {
  expect(JSON.parse(propertyPlaceholder({ field_type: 'list' }))).toEqual(['Item 1', 'Item 2']);
});
