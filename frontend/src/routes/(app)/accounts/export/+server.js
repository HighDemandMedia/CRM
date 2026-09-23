import { error } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { exportCompanies } from '$lib/server/v2/company-csv.js';

/** @type {import('./$types').RequestHandler} */
export async function GET(event) {
  try {
  await apiRequest('/roles/export/companies/', {}, {cookies:event.cookies});
  } catch (e) {
    const failure = /** @type {Error & {status?: number}} */ (e);
    error(failure.status || 500, failure.message || 'Could not export records.');
  }
  event.url.searchParams.set('permission_action','export');
  const csv = await exportCompanies(event);
  return new Response(csv, {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': 'attachment; filename="companies.csv"',
      'Cache-Control': 'no-store'
    }
  });
}
