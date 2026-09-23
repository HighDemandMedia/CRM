import { configuredStages } from '$lib/v2/pipeline-config.js';
import { companyStages as defaultCompanyStages } from '$lib/v2/company-stages.js';
import { fail } from '@sveltejs/kit';
import { listAccounts, updateAccount } from '$lib/server/v2/accounts.js';
import { companyQuery } from '$lib/server/v2/company-query.js';
import { readableError, stageRequirements } from '$lib/server/v2/form-errors.js';
/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies, url, parent }) {
  const companyStages = configuredStages((await parent()).pipelineConfig, 'Account', defaultCompanyStages);
  const query = companyQuery(url),
    view = url.searchParams.get('view') === 'pipeline' ? 'pipeline' : 'list';
  if (view === 'pipeline') query.set('include_pipeline_totals', 'true');
  const pageSize = 25,
    offset = Math.max(0, parseInt(url.searchParams.get('offset') ?? '0') || 0);
  query.set('limit', String(pageSize));
  query.set('offset', String(view === 'list' ? offset : 0));
  const response = await listAccounts({ cookies }, query);
  const board =
    view === 'pipeline'
      ? await Promise.all(
          companyStages
            .filter((source) => !query.get('stage') || source.value === query.get('stage'))
            .map(async (source) => {
              const offset = Math.max(
                0,
                parseInt(url.searchParams.get(`${source.value}_offset`) ?? '0') || 0
              );
              const params = new URLSearchParams(query);
              params.set('stage', source.value);
              params.set('offset', String(offset));
              const rows = await listAccounts({ cookies }, params);
              return {
                ...source,
                contacts: rows.results,
                count: rows.totals.count,
                moneyTotals: rows.totals.money_totals,
                offset
              };
            })
        )
      : [];
  return {
    view,
    companies: response.results,
    totals: response.totals,
    stages: companyStages,
    board,
    offset,
    pageSize,
    contacts: response.contacts,
    industries: response.industries,
    countries: response.countries,
    search: query.get('search') ?? ''
  };
}
/** @type {import('./$types').Actions} */
export const actions = {
  moveStage: async ({ cookies, request }) => {
    const form = await request.formData();
    const id = String(form.get('id') ?? ''),
      source = String(form.get('stage') ?? '');
    if (!/^[0-9a-f-]{36}$/i.test(id) || !source)
      return fail(400, { error: 'Choose a valid company and stage.' });
    try {
      await updateAccount({ cookies }, id, { stage: source });
      return { moved: true };
    } catch (/** @type {any} */ err) {
      return fail(400, { stageRequirements: stageRequirements(err), error: readableError(err, 'Could not move company.') });
    }
  }
};
