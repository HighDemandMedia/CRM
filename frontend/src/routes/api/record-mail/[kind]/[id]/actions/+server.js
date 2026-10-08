import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

export async function POST({ cookies, params, request }) {
  const headers = { 'Cache-Control': 'private, no-store' };
  if (!['contact', 'company'].includes(params.kind) || !/^[0-9a-f-]{36}$/i.test(params.id))
    return json({ error: 'Invalid record.' }, { status: 400, headers });
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'Invalid request.' }, { status: 400, headers });
  }
  try {
    return json(
      await apiRequest(
        `/integrations/google/records/${params.kind}/${params.id}/mail/actions/`,
        { method: 'POST', body },
        { cookies }
      ),
      { headers }
    );
  } catch (error) {
    const status = [400, 401, 403, 404, 409, 429].includes(error?.status) ? error.status : 503;
    return json(
      {
        error:
          status === 503
            ? 'Sending could not be confirmed. Check Gmail Sent before trying again.'
            : error.message
      },
      { status, headers }
    );
  }
}
