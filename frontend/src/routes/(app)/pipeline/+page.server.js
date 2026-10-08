import { listPagination, checkListPage } from '$lib/server/v2/pagination.js';
import { pipelineColumns } from '$lib/server/v2/pipeline-columns.js';
import { configuredStages } from '$lib/v2/pipeline-config.js';
import { fail } from '@sveltejs/kit';
import { listDeals, moveDeal } from '$lib/server/v2/deals.js';
import { dealQuery } from '$lib/server/v2/deal-query.js';
import { getOrgPeopleAndTeams } from '$lib/server/v2/org-people.js';
import { readableError, stageRequirements } from '$lib/server/v2/form-errors.js';
import { STAGES, STAGE_LABEL } from '$lib/v2/enums.js';
/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies, url, parent }) {
  const view = ['pipeline', 'board'].includes(url.searchParams.get('view') ?? '')
    ? 'pipeline'
    : 'list';
  const query = dealQuery(url);
  if (view === 'pipeline') {
    query.set('include_pipeline_totals', 'true');
    query.set('board', 'true');
    // The API validates/clamps offsets and only reads configured stages.
    for (const [key, value] of url.searchParams) {
      if (key.endsWith('_offset')) query.set(key, value);
    }
  }
  const { pageSize, offset } = listPagination(url, view === 'list');
  query.set('limit', String(pageSize));
  query.set('offset', String(view === 'list' ? offset : 0));
  const [response, people, shell] = await Promise.all([
    listDeals({ cookies }, query),
    getOrgPeopleAndTeams(cookies),
    parent()
  ]);
  checkListPage(url, { pageSize, offset }, response.totals.count);
  const stages = configuredStages(
    shell.pipelineConfig,
    'Opportunity',
    STAGES.map((value) => ({ value, label: STAGE_LABEL[value] }))
  );
  const board =
    view === 'pipeline'
      ? await pipelineColumns(response, stages, query, (params) => listDeals({ cookies }, params))
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
    if (!/^[0-9a-f-]{36}$/i.test(id) || !stage)
      return fail(400, { error: 'Choose a valid deal and stage.' });
    try {
      await moveDeal({ cookies }, id, { columnId: stage, aboveId: '', belowId: '' });
      return { moved: true };
    } catch (/** @type {any} */ err) {
      return fail(400, {
        stageRequirements: stageRequirements(err),
        error: readableError(err, 'Could not move deal.')
      });
    }
  }
};
