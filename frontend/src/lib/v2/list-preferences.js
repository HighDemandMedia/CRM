export function browserStorage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/** Browser-only presentation preferences; no records, permissions or credentials. */
export function preferenceKey(kind, scope) {
  return `crm.list.${kind}.v1.${scope}`;
}

export function readPreference(storage, key, fallback) {
  try {
    return JSON.parse(storage.getItem(key) ?? 'null') ?? fallback;
  } catch {
    return fallback;
  }
}

export function writePreference(storage, key, value) {
  try {
    storage.setItem(key, JSON.stringify(value));
  } catch {
    // Browser privacy settings may disable storage; the current view still works.
  }
}

export function columnWidths(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  return Object.fromEntries(
    Object.entries(value).filter(
      ([, width]) =>
        typeof width === 'number' && Number.isFinite(width) && width >= 60 && width <= 2000
    )
  );
}

const VIEW_KEYS = ['view', 'sort', 'direction'];
export function viewPreferences(params) {
  return Object.fromEntries(
    VIEW_KEYS.flatMap((key) => {
      const value = params.get(key);
      if (!value || value.length > 150) return [];
      if (key === 'view' && !['list', 'pipeline'].includes(value)) return [];
      if (key === 'direction' && !['asc', 'desc'].includes(value)) return [];
      return [[key, value]];
    })
  );
}
