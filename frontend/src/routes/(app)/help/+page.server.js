import { randomUUID } from 'node:crypto';
import { fail } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { readableError } from '$lib/server/v2/form-errors.js';
import { requestTypes } from '$lib/help/request-types.js';

export async function load({ cookies }) {
  return { support: await apiRequest('/help/requests/', {}, { cookies }), requestId: randomUUID() };
}
export const actions = {
  default: async ({ cookies, request }) => {
    const form = await request.formData();
    const category = String(form.get('category') || '');
    const type = requestTypes.find((item) => item.key === category);
    const values = Object.fromEntries(
      [
        'request_id',
        'category',
        'area',
        'subject',
        ...(type?.fields.map((field) => field.key) || [])
      ].map((key) => [key, String(form.get(key) || '').trim()])
    );
    if (!type) return fail(400, { error: 'Choose a request type.', values });
    try {
      const receipt = await apiRequest(
        '/help/requests/',
        { method: 'POST', body: values },
        { cookies }
      );
      return { receipt };
    } catch (cause) {
      return fail([400, 409, 429, 503].includes(cause.status) ? cause.status : 500, {
        error: readableError(cause, 'Could not send your request. Please try again.'),
        values
      });
    }
  }
};
