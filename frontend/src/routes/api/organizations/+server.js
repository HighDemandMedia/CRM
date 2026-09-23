import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';

/** @type {import('./$types').RequestHandler} */
export async function GET({cookies}) {
  const memberships = await apiRequest('/org/', {}, {cookies});
  const organizations = (memberships.profile_org_list || [])
    .filter(membership => membership.org?.id)
    .map(membership => ({id:membership.org.id, name:membership.org.name}));
  return json({organizations}, {headers:{'Cache-Control':'private, no-store'}});
}
