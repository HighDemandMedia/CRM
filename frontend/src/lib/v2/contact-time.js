/** @param {string|null|undefined} iso */
export function exactTime(iso) {
  if (!iso) return 'Not recorded';
  const date = new Date(iso);
  if (!Number.isFinite(date.getTime())) return 'Not recorded';
  return date.toLocaleString('en-US', {
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
export function stageDuration(iso, now) {
  const entered = iso ? Date.parse(iso) : NaN;
  if (!Number.isFinite(entered)) return '';
  const days = Math.floor(Math.max(0, now - entered) / 86400000);
  if (days === 0) return '';
  return `${days} ${days === 1 ? 'day' : 'days'}`;
}
