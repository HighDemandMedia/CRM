import { isRecordId } from '$lib/identifiers.js';
import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { mailAttachmentError } from '$lib/v2/mail-composition.js';

export async function POST({ cookies, params, request }) {
  const headers = { 'Cache-Control': 'private, no-store' };
  if (!['contact', 'company'].includes(params.kind) || !isRecordId(params.id))
    return json({ error: 'Invalid record.' }, { status: 400, headers });
  let body;
  try {
    if (request.headers.get('content-type')?.startsWith('multipart/form-data')) {
      body = await request.formData();
      const files = body.getAll('attachments');
      if (files.some((file) => !(file instanceof File)))
        return json({ error: 'Invalid attachment.' }, { status: 400, headers });
      const error = mailAttachmentError(/** @type {File[]} */ (files));
      if (error) return json({ error }, { status: 400, headers });
    } else body = await request.json();
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
