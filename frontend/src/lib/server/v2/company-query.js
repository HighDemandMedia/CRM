import { advancedCompanyFilters } from '$lib/v2/company-filter-fields.js';
/** @param {URL} url */
export function companyQuery(url) {
  const params = new URLSearchParams();
  for (const key of [
    'search',
    'contacts',
    'source',
    'stage',
    ...advancedCompanyFilters.flatMap((field) =>
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
export const companySources = [
  { value: 'META', label: 'Meta' },
  { value: 'GOOGLE', label: 'Google' },
  { value: 'TIKTOK', label: 'TikTok' },
  { value: 'ORGANIC', label: 'Organic' },
  { value: 'CALL', label: 'Call' },
  { value: 'CUSTOMER_REFERAL', label: 'Customer Referal' },
  { value: 'EMPLOYER_REFERAL', label: 'Employer Referal' },
  { value: 'WALK_IN', label: 'Walk In' },
  { value: 'UNASSIGNED', label: 'No source' }
];
