import { exportQueryURL, exportRows } from './export-scope.js';
import { apiRequest } from '$lib/api-helpers.js';
import { listColumns, columnValue } from '$lib/v2/list-columns.js';
import { dealColumns } from '$lib/v2/deal-columns.js';
import { listDeals } from './deals.js';
import { dealQuery } from './deal-query.js';

/** @param {unknown} value */
export function csvCell(value) {
  let text = String(value ?? '');
  // Treat user text as text when the CSV is opened in a spreadsheet.
  if (/^[\s\uFEFF]*[=+\-@]/.test(text) || /^[\t\r\n]/.test(text)) text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
}
/** @param {any} contact @param {string} key */
function exportValue(contact, key, catalog) {
  if (key === 'contacts')
    return (contact.contacts ?? [])
      .map((c) => c.name || [c.first_name, c.last_name].filter(Boolean).join(' '))
      .join('; ');
  if (key === 'pages') return (contact.pages ?? []).map((p) => `${p.name}: ${p.url}`).join('; ');
  if (key === 'amount')
    return contact.amount == null ? '' : `${contact.amount} ${contact.currency}`;
  if (key === 'account') return contact.account?.id ? contact.account.name : '';
  if (key === 'owner')
    return contact.owner
      ? `${contact.owner}${contact.owner_count > 1 ? ` +${contact.owner_count - 1}` : ''}`
      : '';
  if (key === 'is_active' || key === 'do_not_call') return contact[key] ? 'Yes' : 'No';
  if (!key.startsWith('custom_fields.') && (contact[key] === null || contact[key] === undefined))
    return '';
  return columnValue(contact, key, catalog);
}
/** @param {any} event */
export async function exportDeals(event) {
  const context = await apiRequest('/org/ui-context/', {}, { cookies: event.cookies });
  const catalog = listColumns('Opportunity', context.property_layout?.Opportunity, dealColumns);
  const available = catalog.map((c) => [c.key, c.label]);
  const requested = [
    ...new Set(
      (
        event.url.searchParams.get('columns') ??
        catalog
          .filter((c) => c.system)
          .map((c) => c.key)
          .join(',')
      ).split(',')
    )
  ];
  const columns = requested
    .map((key) => available.find(([id]) => id === key))
    .filter((column) => column !== undefined);
  if (!columns.length) throw new Error('Choose at least one valid column.');
  const lines = [columns.map(([, label]) => csvCell(label)).join(',')];
  const query = dealQuery(exportQueryURL(event.url));
  for await (const contact of exportRows(event, query, listDeals)) {
    lines.push(columns.map(([key]) => csvCell(exportValue(contact, key, catalog))).join(','));
  }
  return '\uFEFF' + lines.join('\r\n') + '\r\n';
}
