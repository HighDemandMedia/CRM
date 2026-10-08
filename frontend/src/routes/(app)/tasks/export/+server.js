import { error } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { postExport } from '$lib/server/v2/export-scope.js';
import { exportQueue } from '$lib/server/v2/queue-csv.js';

export async function GET(event) {
  try {
    await apiRequest('/roles/export/tasks/', {}, { cookies: event.cookies });
  } catch (failure) {
    error(failure.status || 500, 'Could not export records.');
  }
  return new Response(await exportQueue(event, 'Task'), {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': 'attachment; filename="tasks.csv"',
      'Cache-Control': 'private, no-store'
    }
  });
}
export const POST = (event) => postExport(event, GET);
