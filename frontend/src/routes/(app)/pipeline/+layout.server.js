import { getOrgPeopleAndTeams } from '$lib/server/v2/org-people.js';
import { getTags } from '$lib/server/v2/tags.js';

// Keep authorized options across view switches without refetching on every filter.
/** @type {import('./$types').LayoutServerLoad} */
export async function load({ cookies, depends }) {
  depends('crm:deal-options');
  const [people, tags] = await Promise.all([
    getOrgPeopleAndTeams(cookies, { module: 'deals' }),
    getTags({ cookies }, { compact: true })
  ]);
  return { people: people.people, tags: tags.tags };
}
