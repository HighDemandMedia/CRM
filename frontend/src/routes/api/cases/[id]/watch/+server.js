import { isRecordId } from '$lib/identifiers.js';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').RequestHandler} */
export async function POST({ params, cookies, locals }) {
  if (!isRecordId(params.id)) return new Response(null, { status: 400 });
  const data = await apiRequest(
    `/cases/${params.id}/watch/`,
    { method: 'POST' },
    { cookies, org: locals?.org }
  );
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
}

/** @type {import('./$types').RequestHandler} */
export async function DELETE({ params, cookies, locals }) {
  if (!isRecordId(params.id)) return new Response(null, { status: 400 });
  await apiRequest(
    `/cases/${params.id}/watch/`,
    { method: 'DELETE' },
    { cookies, org: locals?.org }
  );
  return new Response(null, { status: 204 });
}
