import { savePasswordSession } from '$lib/server/password-session.js';
import { listTimezones } from '$lib/server/v2/organization.js';
import { fail } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { readableError } from '$lib/server/v2/form-errors.js';
import { getProfile } from '$lib/server/v2/profile.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies }) {
  const [profile, timezones, password] = await Promise.all([getProfile({ cookies }), listTimezones(cookies), apiRequest('/auth/password/change/', {}, { cookies })]);
  return { ...profile, timezones, hasPassword: password.has_password && !password.can_reset_password };
}

/** @type {import('./$types').Actions} */
export const actions = {
  password: async ({ cookies, request }) => {
    const form = await request.formData();
    if (form.get('password') !== form.get('confirm_password')) return fail(400, { scope: 'password', message: 'Passwords do not match.' });
    try {
      const result = await apiRequest('/auth/password/change/', { method: 'POST', body: { current_password: String(form.get('current_password') || ''), password: String(form.get('password') || '') } }, { cookies });
      savePasswordSession(cookies, result);
      return { scope: 'password', saved: true };
    } catch (err) { return fail(400, { scope: 'password', message: readableError(err, 'Could not change password.') }); }
  },
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
