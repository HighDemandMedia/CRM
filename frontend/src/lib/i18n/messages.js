import es from './es.json';

export function normalizeLocale(value) {
  return value === 'es' ? 'es' : 'en';
}

/** Only authored UI messages belong here; never pass record/user content. */
export function translate(locale, message, values = {}) {
  if (message == null) return '';
  const translated =
    normalizeLocale(locale) === 'es' && Object.hasOwn(es, message) ? es[message] : message;
  return String(translated).replace(/\{(\w+)\}/g, (token, key) =>
    Object.hasOwn(values, key) ? String(values[key]) : token
  );
}

export function intlLocale(locale) {
  return normalizeLocale(locale) === 'es' ? 'es-US' : 'en-US';
}
