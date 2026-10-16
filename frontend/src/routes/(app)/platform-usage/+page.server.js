import { error } from '@sveltejs/kit';
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
