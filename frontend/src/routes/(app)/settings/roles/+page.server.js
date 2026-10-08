import { fail } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { readableError } from '$lib/server/v2/form-errors.js';
export async function load({ cookies }) {
  try {
    return { ...(await apiRequest('/roles/', {}, { cookies })), forbidden: false };
  } catch (err) {
    if (err.status === 403) return { forbidden: true, roles: [] };
    throw err;
  }
}
export const actions = {
  save: async ({ cookies, request }) => {
    const form = await request.formData();
    try {
      const id = String(form.get('id') || '');
      const rules = JSON.parse(String(form.get('rules')));
      await apiRequest(
        id ? `/roles/${id}/` : '/roles/',
        {
          method: id ? 'PATCH' : 'POST',
          body: {
            scope: String(form.get('scope') || 'own'),
            name: String(form.get('name') || '').trim(),
            description: String(form.get('description') || ''),
            rules,
            settings_access: JSON.parse(String(form.get('settings_access') || '{}'))
          }
        },
        { cookies }
      );
      return { saved: true };
    } catch (err) {
      return fail(err?.status === 403 ? 403 : 400, {
        error: readableError(err, 'Could not save role.')
      });
    }
  }
};
