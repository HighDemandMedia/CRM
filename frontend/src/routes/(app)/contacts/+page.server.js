import { listPagination, checkListPage } from '$lib/server/v2/pagination.js';
import { pipelineColumns } from '$lib/server/v2/pipeline-columns.js';
import { configuredStages } from '$lib/v2/pipeline-config.js';
import { fail } from '@sveltejs/kit';
import { readableError, stageRequirements } from '$lib/server/v2/form-errors.js';
import { listContacts, updateContact } from '$lib/server/v2/contacts.js';
import { contactQuery } from '$lib/server/v2/contact-query.js';
import { getOrgPeopleAndTeams, resolveMe } from '$lib/server/v2/org-people.js';
import { getTags } from '$lib/server/v2/tags.js';

/**
 * Only filters the API actually applies are forwarded. A parameter that
 * changes the URL and nothing else teaches people the filter bar is decorative.
 *
 * `inactive=1` in the URL is kept from the fixture page, because the question
 * it asks is a good one, but it is answered by the API now (`?is_active=`)
 * rather than by discarding rows after they arrive, which was only ever right
 * on the first page.
 *
 * The pickers are fetched here rather than inside `listContacts` for the same
 * reason as `tickets.js`: a picker fetch folded into the list read would cost
 * a redundant request on every caller that reads contacts for their totals
 * alone.
 *
 * @type {import('./$types').PageServerLoad}
 */
export async function load({ cookies, url, locals, parent }) {
  const params = contactQuery(url);
  const includeInactive = url.searchParams.get('inactive') === '1';

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
  const [response, orgPeople, tagList, shell] = await Promise.all([
    listContacts({ cookies }, params),
    getOrgPeopleAndTeams(cookies),
    // A failed tag fetch should cost the Tag dropdown in the filter bar, not
    // the whole list. Follows the tickets.js pattern; see the note there.
    getTags({ cookies }).catch(() => ({ tags: [] })),
    parent()
  ]);

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
    people: orgPeople.people,
    tags: tagList.tags ?? [],
    meId: resolveMe(orgPeople.people, /** @type {any} */ (locals).user?.email)
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
