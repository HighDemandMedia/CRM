import { getOrgPeopleAndTeams, resolveMe } from '$lib/server/v2/org-people.js';

/** @type {import('./$types').LayoutServerLoad} */
export async function load({ cookies, locals, depends }) {
  depends('crm:task-options');
  const orgPeople = await getOrgPeopleAndTeams(cookies, { module: 'tasks' });
  return {
    people: orgPeople.people,
    meId: resolveMe(orgPeople.people, /** @type {any} */ (locals).user?.email)
  };
}
