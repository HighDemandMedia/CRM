import { error } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { listColumns, columnValue } from '$lib/v2/list-columns.js';
import { listTasks } from './tasks.js';
import { listTickets } from './tickets.js';
import { taskQuery, ticketQuery } from './queue-query.js';
import { exportQueryURL, exportRows } from './export-scope.js';
import { csvCell } from './contact-csv.js';

export async function exportQueue(event, target) {
  const context = await apiRequest('/org/ui-context/', {}, { cookies: event.cookies });
  const catalog = listColumns(
    target,
    context.property_layout?.[target],
    target === 'Case' ? [['association', 'Associated with']] : []
  );
  const requested = [
    ...new Set(
      (
        event.url.searchParams.get('columns') ||
        catalog
          .filter((column) => column.system)
          .map((column) => column.key)
          .join(',')
      ).split(',')
    )
  ];
  const columns = requested
    .map((key) => catalog.find((column) => column.key === key))
    .filter(Boolean);
  if (!columns.length) error(400, 'Choose at least one valid column.');
  const lines = [columns.map((column) => csvCell(column.label)).join(',')];
  const url = exportQueryURL(event.url);
  const query = target === 'Task' ? taskQuery(url) : ticketQuery(url, context.pipelines);
  for await (const row of exportRows(event, query, target === 'Task' ? listTasks : listTickets)) {
    if (
      target === 'Task' &&
      url.searchParams.get('all') === '0' &&
      !query.get('status') &&
      row.is_done
    )
      continue;
    lines.push(
      columns
        .map(({ key }) =>
          csvCell(
            key === 'association'
              ? [row.account?.name, ...(row.contacts ?? []).map((c) => c.name)]
                  .filter(Boolean)
                  .join(', ')
              : columnValue(row, key, catalog)
          )
        )
        .join(',')
    );
  }
  return '\uFEFF' + lines.join('\r\n') + '\r\n';
}
