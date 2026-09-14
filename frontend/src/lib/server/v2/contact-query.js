import { advancedContactFilters } from '$lib/v2/contact-filter-fields.js';
import { FILTER_FIELDS } from './contacts.js';
import { readFilters, buildFilterQuery } from './filter-params.js';

/** Shared query for the list and CSV export. @param {URL} url */
export function contactQuery(url) {
  const params = buildFilterQuery(FILTER_FIELDS, readFilters(url, 'contacts'));
  for (const key of [
    'search',
    'stage',
    ...advancedContactFilters.flatMap((field) =>
      field.type === 'range' ? [`${field.key}__gte`, `${field.key}__lte`] : [field.key]
    )
  ]) {
    const value = url.searchParams.get(key);
    if (value) params.set(key, value);
  }
  if (url.searchParams.get('inactive') !== '1') params.set('is_active', 'true');
  params.set('sort', url.searchParams.get('sort') ?? '');
  params.set('direction', url.searchParams.get('direction') === 'desc' ? 'desc' : 'asc');
  return params;
}
