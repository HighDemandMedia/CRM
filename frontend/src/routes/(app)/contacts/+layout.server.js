import { getOrgPeopleAndTeams, resolveMe } from '$lib/server/v2/org-people.js';
import { getTags } from '$lib/server/v2/tags.js';

// Route-scoped data is retained across filters, pagination and view switches.
// No shared server cache: switching sessions/organizations invalidates the layouts.
/** @type {import('./$types').LayoutServerLoad} */
export async function load({ cookies, locals, depends }) {
  depends('crm:contact-options');
  const [people, tags] = await Promise.all([
    getOrgPeopleAndTeams(cookies, { module: 'contacts' }),
    getTags({ cookies }, { compact: true }).catch(() => ({ tags: [] }))
  ]);
  return {
    people: people.people,
    tags: tags.tags,
    meId: resolveMe(people.people, locals.user?.email)
  };
}
