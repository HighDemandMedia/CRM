import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

const modules = new Set(['contacts', 'companies', 'deals', 'tasks', 'tickets']);
const headers = { 'Cache-Control': 'private, no-store' };
function failure(error) {
  const status = error.status >= 400 && error.status < 600 ? error.status : 500;
  return json(
    {
      message:
        status >= 500
          ? 'Could not complete the import. Retry the same file to check its result.'
          : error.message,
      errors: error.body?.errors ?? []
    },
    { status, headers }
  );
}
export async function GET({ cookies, params }) {
  if (!modules.has(params.module)) return json({ message: 'Unknown object.' }, { status: 404 });
  try {
    return json(await apiRequest(`/record-import/${params.module}/`, {}, { cookies }), { headers });
  } catch (error) {
    return failure(error);
  }
}
export async function POST({ cookies, params, request }) {
  if (!modules.has(params.module)) return json({ message: 'Unknown object.' }, { status: 404 });
  try {
    const body = await request.formData();
    const file = body.get('file');
    if (!file || typeof file === 'string' || file.size > 2 * 1024 * 1024)
      return json({ message: 'Choose a CSV file of 2 MB or less.' }, { status: 400, headers });
    return json(
      await apiRequest(`/record-import/${params.module}/`, { method: 'POST', body }, { cookies }),
      { headers }
    );
  } catch (error) {
    return failure(error);
  }
}
