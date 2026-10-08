import { error } from '@sveltejs/kit';

/** Preserve legacy exports as filtered exports; never silently broaden an unknown scope. */
export function exportQueryURL(url) {
  const scope = url.searchParams.get('scope') || 'filtered';
  if (!['filtered', 'all', 'page'].includes(scope)) error(400, 'Choose a valid export scope.');
  const queryURL = new URL(url);
  if (scope === 'all') {
    queryURL.search = '';
    for (const key of ['sort', 'direction']) {
      const value = url.searchParams.get(key);
      if (value) queryURL.searchParams.set(key, value);
    }
    queryURL.searchParams.set('inactive', '1');
  }
  return queryURL;
}

/** The browser supplies IDs, never record contents; the API rechecks export access. */
export async function postExport(event, handler) {
  const body = await event.request.formData();
  const ids = body.getAll('ids').map(String);
  if (
    ids.length > 1000 ||
    ids.some((id) => !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id))
  )
    error(400, 'Invalid records for export.');
  return handler({ ...event, exportIds: [...new Set(ids)] });
}

/** Page through authorized results. Current-page exports preserve the displayed row order. */
export async function* exportRows(event, query, list) {
  const current = event.url.searchParams.get('scope') === 'page';
  if (current && !Array.isArray(event.exportIds)) error(400, 'Choose the records to export.');
  const ids = current ? event.exportIds : null;
  if (ids?.length === 0) return;
  const wanted = ids ? new Set(ids) : null;
  const found = new Map();
  query.set('limit', '100');
  query.set('permission_action', 'export');
  let offset = 0;
  while (true) {
    if (event.request?.signal.aborted) throw new Error('Export canceled.');
    query.set('offset', String(offset));
    const page = await list({ cookies: event.cookies }, query);
    for (const row of page.results) {
      if (wanted) {
        if (wanted.has(row.id)) found.set(row.id, row);
      } else yield row;
    }
    offset += page.results.length;
    if (
      (wanted && found.size === wanted.size) ||
      offset >= page.totals.count ||
      !page.results.length
    )
      break;
  }
  if (ids) for (const id of ids) if (found.has(id)) yield found.get(id);
}
