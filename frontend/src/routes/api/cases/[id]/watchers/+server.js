import { isRecordId } from '$lib/identifiers.js';
import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').RequestHandler} */
export async function GET({ params, cookies, locals }) {
  if (!isRecordId(params.id)) return json({ watchers: [], count: 0 }, { status: 400 });
  const data = await apiRequest(`/cases/${params.id}/watchers/`, {}, { cookies, org: locals?.org });
  return json(data);
}
