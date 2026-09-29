import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { readableError } from '$lib/server/v2/form-errors.js';

/** @type {import('./$types').RequestHandler} */
export async function DELETE({ cookies, params, request, url }) {
  if (request.headers.get('origin') !== url.origin)
    return json({ message: 'Invalid request origin.' }, { status: 403 });
  if (!cookies.get('jwt_access'))
    return json({ message: 'Please sign in again.' }, { status: 401 });
  try {
    return json(await apiRequest(`/attachments/${params.id}/`, { method: 'DELETE' }, { cookies }));
  } catch (/** @type {any} */ err) {
    return json(
      { message: readableError(err, 'Could not delete this attachment.') },
      { status: err.status >= 400 && err.status <= 599 ? err.status : 502 }
    );
  }
}
