import { fail } from '@sveltejs/kit';
import { listDeals, moveDeal } from '$lib/server/v2/deals.js';
import { dealQuery } from '$lib/server/v2/deal-query.js';
import { getOrgPeopleAndTeams } from '$lib/server/v2/org-people.js';
import { readableError } from '$lib/server/v2/form-errors.js';
import { STAGES, STAGE_LABEL } from '$lib/v2/enums.js';
/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies, url }) {
  const view = ['pipeline', 'board'].includes(url.searchParams.get('view') ?? '')
    ? 'pipeline'
    : 'list';
  const query = dealQuery(url),
    pageSize = 25;
  const offset = Math.max(0, parseInt(url.searchParams.get('offset') ?? '0') || 0);
  query.set('limit', String(pageSize));
  query.set('offset', String(view === 'list' ? offset : 0));
  const [response, people] = await Promise.all([
    listDeals({ cookies }, query),
    getOrgPeopleAndTeams(cookies)
  ]);
  const stages = STAGES.map((value) => ({ value, label: STAGE_LABEL[value] }));
  const board =
    view === 'pipeline'
      ? await Promise.all(
          stages
            .filter((s) => !query.get('stage') || query.get('stage') === s.value)
            .map(async (stage) => {
              const params = new URLSearchParams(query);
              const offset = Math.max(
                0,
                parseInt(url.searchParams.get(`${stage.value}_offset`) ?? '0') || 0
              );
              params.set('stage', stage.value);
              params.set('offset', String(offset));
              const result = await listDeals({ cookies }, params);
              return { ...stage, contacts: result.results, count: result.totals.count, offset };
            })
        )
      : [];
  return {
    view,
    deals: response.results,
    totals: response.totals,
    contacts: response.contacts,
    accounts: response.accounts,
    people: people.people,
    stages,
    board,
    pageSize,
    offset
  };
}
/** @type {import('./$types').Actions} */
export const actions = {
  moveStage: async ({ cookies, request }) => {
    const form = await request.formData(),
      id = String(form.get('id') ?? ''),
      stage = String(form.get('stage') ?? '');
    if (!/^[0-9a-f-]{36}$/i.test(id) || !STAGES.includes(stage))
      return fail(400, { error: 'Choose a valid deal and stage.' });
    try {
      await moveDeal({ cookies }, id, { columnId: stage, aboveId: '', belowId: '' });
      return { moved: true };
    } catch (/** @type {any} */ err) {
      return fail(400, { error: readableError(err, 'Could not move deal.') });
    }
  }
};
