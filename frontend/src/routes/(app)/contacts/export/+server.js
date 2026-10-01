import { error } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { exportContacts } from '$lib/server/v2/contact-csv.js';

/** @type {import('./$types').RequestHandler} */
export async function GET(event) {
  try {
    await apiRequest('/roles/export/contacts/', {}, { cookies: event.cookies });
  } catch (e) {
    const failure = /** @type {Error & {status?: number}} */ (e);
    error(failure.status || 500, failure.message || 'Could not export records.');
  }
  event.url.searchParams.set('permission_action', 'export');
  const csv = await exportContacts(event);
  return new Response(csv, {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': 'attachment; filename="contacts.csv"',
      'Cache-Control': 'no-store'
    }
  });
}
