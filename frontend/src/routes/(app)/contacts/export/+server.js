import { exportContacts } from '$lib/server/v2/contact-csv.js';

/** @type {import('./$types').RequestHandler} */
export async function GET(event) {
  const csv = await exportContacts(event);
  return new Response(csv, {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': 'attachment; filename="contacts.csv"',
      'Cache-Control': 'no-store'
    }
  });
}
