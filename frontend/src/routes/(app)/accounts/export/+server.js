import { exportCompanies } from '$lib/server/v2/company-csv.js';

/** @type {import('./$types').RequestHandler} */
export async function GET(event) {
  const csv = await exportCompanies(event);
  return new Response(csv, {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': 'attachment; filename="companies.csv"',
      'Cache-Control': 'no-store'
    }
  });
}
