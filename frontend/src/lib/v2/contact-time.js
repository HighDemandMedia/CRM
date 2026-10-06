/** @param {string|null|undefined} iso */
export function exactTime(iso, locale = 'en-US') {
  if (!iso) return locale.startsWith('es') ? 'Sin registrar' : 'Not recorded';
  const date = new Date(iso);
  if (!Number.isFinite(date.getTime()))
    return locale.startsWith('es') ? 'Sin registrar' : 'Not recorded';
  return date.toLocaleString(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
    timeZoneName: 'short'
  });
}

/** @param {string|null|undefined} iso @param {number} now */
export function stageDuration(iso, now, locale = 'en-US') {
  const entered = iso ? Date.parse(iso) : NaN;
  if (!Number.isFinite(entered)) return '';
  const days = Math.floor(Math.max(0, now - entered) / 86400000);
  if (days === 0) return '';
  return new Intl.NumberFormat(locale, { style: 'unit', unit: 'day', unitDisplay: 'long' }).format(
    days
  );
}
