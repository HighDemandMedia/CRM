import { listTimezones } from '$lib/server/v2/organization.js';
import { fail } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { readableError } from '$lib/server/v2/form-errors.js';
import { getProfile } from '$lib/server/v2/profile.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies }) {
  const [profile, timezones] = await Promise.all([getProfile({ cookies }), listTimezones(cookies)]);
  return { ...profile, timezones };
}

/** @type {import('./$types').Actions} */
export const actions = {
  emailMode: async ({ cookies, request }) => {
    const form = await request.formData();
    try {
      await apiRequest('/profile/', { method: 'PATCH', body: { email_integration_mode: String(form.get('email_integration_mode') || '') } }, { cookies });
      return { scope: 'email', saved: true };
    } catch (err) { return fail(400, { scope: 'email', message: readableError(err, 'Could not save email preference.') }); }
  },
  // Only forward editable personal fields; account access is managed separately.
  edit: async ({ cookies, request }) => {
    const form = await request.formData();
    /** @type {Record<string, string>} */
    const body = {};
    for (const field of ['name', 'phone', 'language', 'timezone']) {
      if (form.has(field)) body[field] = form.get(field)?.toString().trim() ?? '';
    }

    try {
      await apiRequest('/profile/', { method: 'PATCH', body }, { cookies });
    } catch (/** @type {any} */ err) {
      return fail(err?.status === 400 ? 400 : 500, {
        values: body,
        message: readableError(err, 'Could not save your profile.')
      });
    }

    return { saved: true };
  }
};
