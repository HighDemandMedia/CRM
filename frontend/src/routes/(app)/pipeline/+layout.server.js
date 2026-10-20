import { getOrgPeopleAndTeams } from '$lib/server/v2/org-people.js';

/** @type {import('./$types').LayoutServerLoad} */
export async function load({ cookies, depends }) {
  depends('crm:deal-options');
  return { people: (await getOrgPeopleAndTeams(cookies, { module: 'deals' })).people };
}
