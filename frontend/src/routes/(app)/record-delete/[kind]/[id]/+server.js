import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { readableError } from '$lib/server/v2/form-errors.js';
export async function GET({ cookies, params, url }) {
  try {
    return json(
      await apiRequest(
        `/record-delete/${params.kind}/${params.id}/?include_associated=${url.searchParams.get('include_associated') === 'true'}`,
        {},
        { cookies }
      ),
      {
        headers: { 'Cache-Control': 'private, no-store' }
      }
    );
  } catch (err) {
    return json(
      { message: readableError(err, 'Could not load deletion details.') },
      { status: 400 }
    );
  }
}
export async function POST({ cookies, params, request }) {
  const body = await request.json();
  try {
    return json(
      await apiRequest(
        `/record-delete/${params.kind}/${params.id}/`,
        { method: 'POST', body },
        { cookies }
      )
    );
  } catch (err) {
    return json({ message: readableError(err, 'Could not delete this record.') }, { status: 400 });
  }
}
