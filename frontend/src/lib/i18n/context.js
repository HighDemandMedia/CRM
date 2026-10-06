import { exactTime, stageDuration } from '$lib/v2/contact-time.js';
import { getContext, setContext } from 'svelte';
import { intlLocale, translate } from './messages.js';

import * as format from '$lib/v2/format.js';

const KEY = Symbol('crm-language');

// A closure per layout/request: no module-level mutable locale shared by users.
export function provideI18n(getLocale) {
  const i18n = {
    exactTime: (value) => exactTime(value, intlLocale(getLocale())),
    stageDuration: (value, now) => stageDuration(value, now, intlLocale(getLocale())),
    ui: (message, values = {}) => translate(getLocale(), message, values),
    locale: () => intlLocale(getLocale()),
    money: (value, currency = 'USD') => format.money(value, currency, intlLocale(getLocale())),
    count: (value) => format.count(value, intlLocale(getLocale())),
    shortDate: (value, now = new Date()) =>
      format.shortDate(value, now, getLocale() === 'es' ? 'es-US' : 'en-GB'),
    longDate: (value) => format.longDate(value, getLocale() === 'es' ? 'es-US' : 'en-GB'),
    relativeDays: (value, now = new Date()) =>
      format.relativeDays(value, now, intlLocale(getLocale())),
    relativeTime: (value, now = new Date()) =>
      format.relativeTime(value, now, intlLocale(getLocale()))
  };
  setContext(KEY, i18n);
  return i18n;
}

export function useI18n() {
  return (
    getContext(KEY) ?? {
      ui: (message, values = {}) => translate('en', message, values),
      locale: () => 'en-US',
      ...format,
      exactTime,
      stageDuration
    }
  );
}
