import { TICKET_SORT_FIELDS } from '$lib/v2/ticket-sort.js';
import { buildFilterQuery, readFilters } from './filter-params.js';
import { FILTER_FIELDS as TASK_FILTERS } from './tasks.js';
import { FILTER_FIELDS as TICKET_FILTERS, OPEN_STATUSES } from './tickets.js';
import { configuredStages } from '$lib/v2/pipeline-config.js';

export function taskQuery(url) {
  const params = buildFilterQuery(TASK_FILTERS, readFilters(url, 'tasks'));
  // Filter before pagination so a page is not depleted by completed tasks.
  if (url.searchParams.get('all') === '0' && !params.has('status'))
    params.set('exclude_completed', 'true');
  const search = url.searchParams.get('q');
  if (search) params.set('search', search);
  return params;
}
export function ticketQuery(url, pipelineConfig) {
  const params = buildFilterQuery(TICKET_FILTERS, readFilters(url, 'tickets'));
  for (const key of ['assigned_to', 'priority', 'category', 'overdue', 'search']) {
    const value = url.searchParams.get(key);
    if (value) params.set(key, value);
  }
  const sort = url.searchParams.get('sort') || '';
  if (Object.hasOwn(TICKET_SORT_FIELDS, sort))
    params.set(
      'ordering',
      (url.searchParams.get('direction') === 'desc' ? '-' : '') + TICKET_SORT_FIELDS[sort]
    );
  const status = url.searchParams.get('status') ?? '';
  if (status) params.set('status', status);
  else if (url.searchParams.get('all') === '0') {
    for (const stage of configuredStages(
      pipelineConfig,
      'Case',
      OPEN_STATUSES.map((value) => ({ value }))
    )) {
      if (!['Resolved', 'Closed', 'Rejected', 'Duplicate'].includes(stage.value))
        params.append('status', stage.value);
    }
  }
  return params;
}
