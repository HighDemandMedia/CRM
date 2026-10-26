import { getOrgPeopleAndTeams, resolveMe } from '$lib/server/v2/org-people.js';
import { getTags } from '$lib/server/v2/tags.js';

/** @type {import('./$types').LayoutServerLoad} */
export async function load({ cookies, locals, depends }) {
  depends('crm:ticket-options');
  const [orgPeople, tagList] = await Promise.all([
    getOrgPeopleAndTeams(cookies, { module: 'tickets' }),
    getTags({ cookies }, { compact: true }).catch(() => ({ tags: [] }))
  ]);
  return {
    people: orgPeople.people,
    tags: tagList.tags ?? [],
    meId: resolveMe(orgPeople.people, /** @type {any} */ (locals).user?.email)
  };
}
