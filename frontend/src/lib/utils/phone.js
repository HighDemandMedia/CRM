import { normalizedPhone, displayPhone, PHONE_ERROR } from './phone-number.js';

/** Compatibility helpers: use the same country-aware policy as record forms. */
/** @param {string} value @param {import('libphonenumber-js').CountryCode} [defaultCountry] */
export async function validatePhoneNumber(value, defaultCountry = 'US') {
  if (!value?.trim()) return { isValid: true };
  const normalized = normalizedPhone(value, defaultCountry);
  return normalized
    ? { isValid: true, formatted: displayPhone(normalized) }
    : { isValid: false, error: PHONE_ERROR };
}

/** @param {string} value @param {import('libphonenumber-js').CountryCode} [defaultCountry] */
export async function formatPhoneNumber(value, defaultCountry = 'US') {
  return displayPhone(normalizedPhone(value, defaultCountry) || value);
}

/** @param {string} value @param {import('libphonenumber-js').CountryCode} [defaultCountry] */
export async function formatPhoneForStorage(value, defaultCountry = 'US') {
  return normalizedPhone(value, defaultCountry) || value;
}
