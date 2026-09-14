import { advancedDealFilters } from '$lib/v2/deal-filter-fields.js';
/** @param {URL} url */
export function dealQuery(url) {
  const params = new URLSearchParams();
  for (const key of [
    'search',
    'assigned_to',
    'priority',
    'stage',
    ...advancedDealFilters.flatMap((field) =>
      field.type?.endsWith('range') ? [`${field.key}__gte`, `${field.key}__lte`] : [field.key]
    )
  ]) {
    const value = url.searchParams.get(key);
    if (value) params.set(key, value);
  }
  params.set('sort', url.searchParams.get('sort') ?? 'name');
  params.set('direction', url.searchParams.get('direction') === 'desc' ? 'desc' : 'asc');
  return params;
}
