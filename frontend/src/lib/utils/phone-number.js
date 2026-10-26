import {
  parsePhoneNumberFromString,
  getCountries,
  getCountryCallingCode
} from 'libphonenumber-js/max';

export const PHONE_ERROR =
  'Enter a valid phone number for the selected country, without an extension.';

/** @param {unknown} value @param {import('libphonenumber-js').CountryCode} [country] */
export function parsePhone(value, country = 'US') {
  if (typeof value !== 'string' || !/^\+?[0-9 ().-]+$/.test(value.trim())) return undefined;
  const phone = parsePhoneNumberFromString(value.trim(), {
    defaultCountry: country,
    extract: false
  });
  return phone && !phone.ext ? phone : undefined;
}

/** @param {unknown} value @param {import('libphonenumber-js').CountryCode} [country] */
export function normalizedPhone(value, country = 'US') {
  const phone = parsePhone(value, country);
  return phone?.isValid() ? phone.number : '';
}

export function displayPhone(value) {
  const phone = parsePhone(value);
  return phone?.isValid() ? phone.formatInternational() : value;
}

export { getCountries, getCountryCallingCode };
