import { preferenceKey, readPreference, viewPreferences } from './list-preferences.js';

const OBJECTS = {
  '/contacts': 'Contact',
  '/accounts': 'Account',
  '/pipeline': 'Opportunity',
  '/tasks': 'Task',
  '/tickets': 'Case'
};

/** Prepare navigation and hover preloads with saved sorting before fetching records.
 * Only presentation parameters are restored; view mode always starts as a list.
 */
export function savedListLinks(storage, accountId, email, currentUrl) {
  if (!accountId || !email) return {};
  return Object.fromEntries(
    Object.entries(OBJECTS).map(([path, object]) => {
      const saved = readPreference(
        storage,
        preferenceKey('view', `${accountId}.${email}.${object}`),
        {}
      );
      const stored = saved && typeof saved === 'object' && !Array.isArray(saved) ? saved : {};
      const params = new URLSearchParams(viewPreferences(new URLSearchParams(stored)));
      // Current sorting can precede the preference-writing effect after navigation.
      if (currentUrl?.pathname === path && currentUrl.search) {
        for (const [key, value] of Object.entries(viewPreferences(currentUrl.searchParams)))
          params.set(key, value);
      }
      return [path, path + (params.size ? `?${params}` : '')];
    })
  );
}
