import { isRecordId } from '$lib/identifiers.js';
import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** Read-only summary endpoint for the case header chip. */
/** @type {import('./$types').RequestHandler} */
export async function GET({ params, cookies, locals }) {
  if (!isRecordId(params.id)) {
    return json({ error: 'invalid case id' }, { status: 400 });
  }
  try {
    const data = await apiRequest(
      `/cases/${params.id}/time-summary/`,
      { method: 'GET' },
      { cookies, org: locals?.org }
    );
    return json(data);
  } catch (err) {
    return json({ error: err?.message || 'Summary failed' }, { status: 400 });
  }
}
