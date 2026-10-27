import { isRecordId } from '$lib/identifiers.js';
import { json } from '@sveltejs/kit';
import { getContactForEdit } from '$lib/server/v2/contacts.js';

/** @type {import('./$types').RequestHandler} */
export async function GET({ cookies, params }) {
  const headers = { 'Cache-Control': 'private, no-store' };
  if (!isRecordId(params.id)) return json({ error: 'Invalid record.' }, { status: 400, headers });
  try {
    // The API checks the current session, organization and record visibility.
    return json(await getContactForEdit({ cookies }, params.id), { headers });
  } catch (error) {
    const status = [400, 401, 403, 404, 429].includes(error?.status) ? error.status : 503;
    return json({ error: 'Could not load contact. Please try again.' }, { status, headers });
  }
}
