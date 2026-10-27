import { isRecordId } from '$lib/identifiers.js';
import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** Tier 3 parent/child: descendant tree (max depth 3). */
/** @type {import('./$types').RequestHandler} */
export async function GET({ params, cookies, locals }) {
  if (!isRecordId(params.id)) {
    return json({ error: 'invalid case id' }, { status: 400 });
  }
  const data = await apiRequest(`/cases/${params.id}/tree/`, {}, { cookies, org: locals?.org });
  return json(data);
}
