import { exportDeals } from '$lib/server/v2/deal-csv.js';

/** @type {import('./$types').RequestHandler} */
export async function GET(event) {
  const csv = await exportDeals(event);
  return new Response(csv, {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': 'attachment; filename="deals.csv"',
      'Cache-Control': 'no-store'
    }
  });
}
