import { postExport } from '$lib/server/v2/export-scope.js';
import { error } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { exportDeals } from '$lib/server/v2/deal-csv.js';

/** @type {import('./$types').RequestHandler} */
export async function GET(event) {
  try {
    await apiRequest('/roles/export/deals/', {}, { cookies: event.cookies });
  } catch (e) {
    const failure = /** @type {Error & {status?: number}} */ (e);
    error(failure.status || 500, failure.message || 'Could not export records.');
  }
  event.url.searchParams.set('permission_action', 'export');
  const csv = await exportDeals(event);
  return new Response(csv, {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': 'attachment; filename="deals.csv"',
      'Cache-Control': 'no-store'
    }
  });
}

export const POST = (event) => postExport(event, GET);
