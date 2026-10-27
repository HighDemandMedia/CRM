import { isRecordId } from '$lib/identifiers.js';
import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').RequestHandler} */
export async function GET({ params, url, cookies, locals }) {
  if (!isRecordId(params.id)) {
    return json({ error: 'invalid case id' }, { status: 400 });
  }
  const qs = url.searchParams.toString();
  const data = await apiRequest(
    `/cases/${params.id}/solution-suggestions/${qs ? `?${qs}` : ''}`,
    {},
    { cookies, org: locals?.org }
  );
  return json(data);
}
