import { error, fail } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { readableError } from '$lib/server/v2/form-errors.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ parent, cookies, url }) {
  const shell = await parent();
  if (!shell.isPlatformOwner) error(403, 'Only the platform owner can view usage.');
  const params = new URLSearchParams();
  for (const key of ['q', 'offset', 'page_size']) {
    if (url.searchParams.has(key)) params.set(key, url.searchParams.get(key));
  }
  try {
    return {
      usage: await apiRequest(`/platform/usage/?${params}`, {}, { cookies }),
      usageError: ''
    };
  } catch (err) {
    if (err.status === 401 || err.status === 403) error(err.status, 'Access denied.');
    return {
      usage: null,
      usageError:
        err.status === 400 ? readableError(err, 'Could not load usage.') : 'Could not load usage.'
    };
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  async limits({ request, cookies }) {
    const form = await request.formData();
    const id = String(form.get('organization_id') || '');
    if (!/^[0-9a-f-]{36}$/i.test(id)) return fail(400, { limitsError: 'Invalid organization.' });
    const limits = {};
    for (const key of [
      'users',
      'contacts',
      'companies',
      'deals',
      'tasks',
      'tickets',
      'appointments'
    ]) {
      const value = String(form.get(key) ?? '').trim();
      if (value && (!/^\d+$/.test(value) || Number(value) > 2147483647)) {
        return fail(400, { limitsError: 'Use whole numbers of zero or more.' });
      }
      limits[key] = value === '' ? null : Number(value);
    }
    try {
      // The API checks the live platform-owner grant; an organization admin
      // cannot authorize this action by forging form data or the page state.
      await apiRequest(
        `/platform/organizations/${id}/limits/`,
        { method: 'PATCH', body: { limits } },
        { cookies }
      );
      return { limitsSaved: true };
    } catch (err) {
      return fail(err.status === 403 ? 403 : 400, {
        limitsError: readableError(err, 'Could not save limits.')
      });
    }
  }
};
