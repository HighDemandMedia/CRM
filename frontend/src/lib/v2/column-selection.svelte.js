import { validColumns } from './list-columns.js';
import { browserStorage, readPreference } from './list-preferences.js';

/** @param {() => any[]} getColumns @param {() => string} getScope */
export function columnSelection(getColumns, getScope) {
  let preference = $state(null);
  // A new version intentionally replaces the former six-column default.
  const storageKey = () => `crm.columns.v2.${getScope()}`;
  $effect(() => {
    const key = storageKey();
    const storage = browserStorage();
    const keys = readPreference(storage, key, null);
    preference = { key, keys };
    function sync(event) {
      if (event.storageArea !== storage || (event.key !== key && event.key !== null)) return;
      let updated = null;
      try {
        updated = JSON.parse(event.newValue || 'null');
      } catch {
        /* Corrupt preferences use defaults. */
      }
      preference = { key, keys: updated };
    }
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  });
  function set(keys) {
    const key = storageKey();
    preference = { key, keys };
    try {
      if (keys === null) localStorage.removeItem(key);
      else localStorage.setItem(key, JSON.stringify(keys));
    } catch {
      /* Keep the current session choice when storage is unavailable. */
    }
  }
  return {
    get selected() {
      return validColumns(preference?.key === storageKey() ? preference.keys : null, getColumns());
    },
    set,
    reset: () => set(null),
    showAll: () => set(getColumns().map((c) => c.key)),
    toggle(key) {
      const current = this.selected;
      if (!current.includes(key)) set([...current, key]);
      else if (current.length > 1) set(current.filter((k) => k !== key));
    }
  };
}
