import { asInternalPath, withoutBase } from '$lib/utils/paths.js';
import { base, resolve } from '$app/paths';
import { SvelteURLSearchParams } from 'svelte/reactivity';
import { goto } from '$app/navigation';
import {
  browserStorage,
  preferenceKey,
  readPreference,
  writePreference,
  viewPreferences
} from './list-preferences.js';

/** Restore sorting on a bare module URL; view mode stays an explicit URL choice. */
export function listViewPreference(getScope, getUrl) {
  let loadedKey = '';
  $effect(() => {
    const key = preferenceKey('view', getScope());
    const url = getUrl();
    if (loadedKey !== key) {
      loadedKey = key;
      const saved = readPreference(browserStorage(), key, {});
      if (!url.search && saved && typeof saved === 'object' && !Array.isArray(saved)) {
        const params = new SvelteURLSearchParams(viewPreferences(new SvelteURLSearchParams(saved)));
        if (params.size) {
          void goto(resolve(asInternalPath(`${withoutBase(url.pathname, base)}?${params}`)), {
            replaceState: true,
            noScroll: true,
            keepFocus: true
          }).catch(() => {
            // A remembered layout must never prevent access to the default list.
          });
          return;
        }
      }
    }
    writePreference(browserStorage(), key, viewPreferences(url.searchParams));
  });
}
