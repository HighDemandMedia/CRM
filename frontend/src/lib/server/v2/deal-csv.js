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
function exportValue(contact, key) {
  if (key === 'contacts')
    return (contact.contacts ?? [])
      .map((c) => [c.first_name, c.last_name].filter(Boolean).join(' '))
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
  return contact[key] ?? '';
}
/** @param {any} event */
export async function exportDeals(event) {
  const requested = [
    ...new Set(
      (
        event.url.searchParams.get('columns') ??
        'name,amount,stage_label,closed_on,owner,priority_label,account,contacts'
      ).split(',')
    )
  ];
  const columns = requested
    .map((key) => dealColumns.find(([id]) => id === key))
    .filter((column) => column !== undefined);
  if (!columns.length) throw new Error('Choose at least one valid column.');
  const lines = [columns.map(([, label]) => csvCell(label)).join(',')];
  const query = dealQuery(event.url);
  query.set('limit', '100');
  query.set('permission_action', 'export');
  let offset = 0;
  while (true) {
    if (event.request?.signal.aborted) throw new Error('Export canceled.');
    query.set('offset', String(offset));
    const page = await listDeals({ cookies: event.cookies }, query);
    for (const contact of page.results)
      lines.push(columns.map(([key]) => csvCell(exportValue(contact, key))).join(','));
    offset += page.results.length;
    if (offset >= page.totals.count || !page.results.length) break;
  }
  return '\uFEFF' + lines.join('\r\n') + '\r\n';
}
