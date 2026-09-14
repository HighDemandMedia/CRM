import { companyColumns } from '$lib/v2/company-columns.js';
import { listAccounts } from './accounts.js';
import { companyQuery } from './company-query.js';

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
  if (key === 'annual_revenue')
    return contact.annual_revenue == null ? '' : `${contact.annual_revenue} ${contact.currency}`;
  if (key === 'account') return contact.account?.name || contact.organization || '';
  if (key === 'owner')
    return contact.owner
      ? `${contact.owner}${contact.owner_count > 1 ? ` +${contact.owner_count - 1}` : ''}`
      : '';
  if (key === 'is_active' || key === 'do_not_call') return contact[key] ? 'Yes' : 'No';
  return contact[key] ?? '';
}
/** @param {any} event */
export async function exportCompanies(event) {
  const requested = [
    ...new Set(
      (
        event.url.searchParams.get('columns') ?? 'name,website,owner,industry,source_label,contacts'
      ).split(',')
    )
  ];
  const columns = requested
    .map((key) => companyColumns.find(([id]) => id === key))
    .filter((column) => column !== undefined);
  if (!columns.length) throw new Error('Choose at least one valid column.');
  const lines = [columns.map(([, label]) => csvCell(label)).join(',')];
  const query = companyQuery(event.url);
  query.set('limit', '100');
  let offset = 0;
  while (true) {
    if (event.request?.signal.aborted) throw new Error('Export canceled.');
    query.set('offset', String(offset));
    const page = await listAccounts({ cookies: event.cookies }, query);
    for (const contact of page.results)
      lines.push(columns.map(([key]) => csvCell(exportValue(contact, key))).join(','));
    offset += page.results.length;
    if (offset >= page.totals.count || !page.results.length) break;
  }
  return '\uFEFF' + lines.join('\r\n') + '\r\n';
}
