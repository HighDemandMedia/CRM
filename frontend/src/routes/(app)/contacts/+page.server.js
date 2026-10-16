import { listPagination, checkListPage } from '$lib/server/v2/pagination.js';
import { pipelineColumns } from '$lib/server/v2/pipeline-columns.js';
import { configuredStages } from '$lib/v2/pipeline-config.js';
import { fail } from '@sveltejs/kit';
import { readableError, stageRequirements } from '$lib/server/v2/form-errors.js';
import { listContacts, updateContact } from '$lib/server/v2/contacts.js';
import { contactQuery } from '$lib/server/v2/contact-query.js';

/**
 * Only filters the API actually applies are forwarded. A parameter that
 * changes the URL and nothing else teaches people the filter bar is decorative.
 *
 * `inactive=1` in the URL is kept from the fixture page, because the question
 * it asks is a good one, but it is answered by the API now (`?is_active=`)
 * rather than by discarding rows after they arrive, which was only ever right
 * on the first page.
 *
 * Picker options belong to the route layout so view switches and pagination
 * reuse them without adding requests to record reads.
 *
 * @type {import('./$types').PageServerLoad}
 */
export async function load({ cookies, url, parent, depends }) {
  const params = contactQuery(url);
  const includeInactive = url.searchParams.get('inactive') === '1';

  depends('crm:contacts');
  const view = url.searchParams.get('view') === 'pipeline' ? 'pipeline' : 'list';
  if (view === 'list') {
    params.set('sort', url.searchParams.get('sort') ?? '');
    params.set('direction', url.searchParams.get('direction') === 'desc' ? 'desc' : 'asc');
  }
  if (view === 'pipeline') {
    params.set('include_pipeline_totals', 'true');
    params.set('board', 'true');
    // The API validates/clamps offsets and only reads configured stages.
    for (const [key, value] of url.searchParams) {
      if (key.endsWith('_offset')) params.set(key, value);
    }
  }
  const { pageSize, offset } = listPagination(url, view === 'list');
  params.set('limit', String(pageSize));
  params.set('offset', view === 'pipeline' ? '0' : String(offset));
  const [response, shell] = await Promise.all([listContacts({ cookies }, params), parent()]);

  const { results, totals, stages: defaultStages } = response;
  checkListPage(url, { pageSize, offset }, totals.count);
  const stages = configuredStages(shell.pipelineConfig, 'Contact', defaultStages);
  const board =
    view === 'pipeline'
      ? await pipelineColumns(response, stages, params, (params) =>
          listContacts({ cookies }, params)
        )
      : [];

  return {
    view,
    board,
    stages,
    offset,
    pageSize,
    contacts: results,
    totals,
    includeInactive,
    search: params.get('search') ?? '',
    people: shell.people,
    tags: shell.tags,
    meId: shell.meId
  };
}

/** @type {import('./$types').Actions} */
export const actions = {
  moveStage: async ({ cookies, request }) => {
    const form = await request.formData();
    const id = String(form.get('id') ?? '');
    const stage = String(form.get('stage') ?? '');
    if (!/^[0-9a-f-]{36}$/i.test(id) || !stage) {
      return fail(400, { error: 'Choose a valid contact and stage.' });
    }
    try {
      await updateContact({ cookies }, id, { stage });
      return { moved: true };
    } catch (/** @type {any} */ err) {
      return fail(400, {
        stageRequirements: stageRequirements(err),
        error: readableError(err, 'Could not move this contact. Please try again.')
      });
    }
  }
};
