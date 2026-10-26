import { expect, it } from 'vitest';
import { normalizedPhone, displayPhone } from './phone-number.js';

it.each([
  ['(202) 555-0123', 'US', '+12025550123'],
  ['+1 202 555 0123', 'US', '+12025550123'],
  ['099 123 456', 'UY', '+59899123456'],
  ['+598 99 123 456', 'US', '+59899123456'],
  ['020 7946 0018', 'GB', '+442079460018'],
  ['+39 02 3661 8300', 'US', '+390236618300']
])('normalizes %s in %s', (raw, country, expected) => {
  expect(
    normalizedPhone(raw, /** @type {import('libphonenumber-js').CountryCode} */ (country))
  ).toBe(expected);
});
it.each([
  '+999123456789',
  '+1202',
  '0123456789',
  '+12025550123 ext 12',
  'Call +12025550123',
  '1+2025550123',
  '+1234567890123456'
])('rejects %s', (raw) => {
  expect(normalizedPhone(raw)).toBe('');
});
it('formats display without changing the storage value or guessing invalid legacy values', () => {
  expect(displayPhone('+59899123456')).toBe('+598 99 123 456');
  expect(displayPhone('12345')).toBe('12345');
});
