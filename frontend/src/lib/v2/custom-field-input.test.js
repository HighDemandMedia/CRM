import { expect, it } from 'vitest';
import { propertyValueError } from './custom-field-input.js';
import { recordFieldError } from '$lib/components/creation/validation.js';
import { fieldErrors } from '$lib/server/v2/form-errors.js';

it.each([
  ['phone', '305555019'],
  ['phone', 'abcdefghij'],
  ['email', 'person@'],
  ['email', 'person.example.com'],
  ['url', 'javascript:alert(1)'],
  ['url', 'ftp://example.com'],
  ['url', 'bad host.com'],
  ['integer', '1.2'],
  ['integer', '9007199254740992'],
  ['number', 'NaN'],
  ['number', '0x12'],
  ['money', '1.001'],
  ['money', '100000000000000'],
  ['percentage', '-1'],
  ['percentage', '101'],
  ['date', '2026-02-30'],
  ['date', '2026-13-01'],
  ['time', '24:00'],
  ['time', '10:60'],
  ['text', 'Line\nBreak']
])('blocks invalid %s values: %s', (type, value) => {
  expect(propertyValueError(type, value)).not.toBe('');
});
it.each([
  ['phone', '+59899123456'],
  ['email', 'person+sales@example.com'],
  ['url', 'example.com'],
  ['url', 'https://example.com/path'],
  ['integer', '0'],
  ['number', '-1.23'],
  ['money', '12345678901234.56'],
  ['percentage', '100'],
  ['date', '2028-02-29'],
  ['time', '23:59:59'],
  ['textarea', 'Line\nBreak'],
  ['text', 'Acme 2 & Co.']
])('accepts valid %s values: %s', (type, value) => {
  expect(propertyValueError(type, value)).toBe('');
});
it('keeps optional blanks and false/zero as valid values', () => {
  expect(propertyValueError('phone', '')).toBe('');
  expect(propertyValueError('phone', '', true)).not.toBe('');
  expect(propertyValueError('checkbox', false, true)).toBe('');
  expect(propertyValueError('integer', 0, true)).toBe('');
});
it('uses property types without confusing custom keys with system field names', () => {
  expect(recordFieldError('custom_fields.city', '1234', false, 'text')).toBe('');
  expect(recordFieldError('custom_fields.secondary_phone', 'abc', false, 'phone')).not.toBe('');
  expect(recordFieldError('phone', 'abc', false, 'tel')).not.toBe('');
  expect(recordFieldError('website', 'bad domain', false, 'text')).not.toBe('');
});
it('maps nested custom-property errors to their actual inputs', () => {
  expect(
    fieldErrors({
      body: { errors: { custom_fields: { phone: ['Invalid phone'], amount: 'Invalid amount' } } }
    })
  ).toEqual({
    'custom_fields.phone': 'Invalid phone',
    'custom_fields.amount': 'Invalid amount'
  });
});
