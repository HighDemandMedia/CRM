import { listPagination, checkListPage } from '$lib/server/v2/pagination.js';
import { updateTicket } from '$lib/server/v2/tickets.js';
import { readableError, stageRequirements } from '$lib/server/v2/form-errors.js';
import { fail } from '@sveltejs/kit';
import {
  listTickets,
  bulkUpdateTickets,
  bulkDeleteTickets,
  summarizeBulk
} from '$lib/server/v2/tickets.js';
import { ticketQuery } from '$lib/server/v2/queue-query.js';
import { parseBulkForm } from '$lib/server/v2/bulk-form.js';

/**
 * Only filters the API actually applies are forwarded. A parameter that
 * changes the URL and nothing else teaches people the filter bar is decorative.
 *
 * The queue defaults to open tickets. `status` is repeatable and the API
 * switches to `status__in` when more than one arrives, so "open" is three
 * values rather than a fourth definition of the word.
 *
 * The pickers are retained in the module layout rather than `listTickets` because
 * `getSettingsHub` calls read functions for their totals alone, and a picker
 * fetch folded into one costs a redundant request on every hub load.
 *
 * @type {import('./$types').PageServerLoad}
 */
export async function load({ cookies, url, parent }) {
  // Only the open-stage preset needs configuration before starting the record request.
  const needsStages = url.searchParams.get('all') === '0' && !url.searchParams.get('status');
  const params = ticketQuery(url, needsStages ? (await parent()).pipelineConfig : undefined);
  const { pageSize, offset } = listPagination(url);
  params.set('limit', String(pageSize));
  params.set('offset', String(offset));
  const status = url.searchParams.get('status') ?? '';
  const showAll = url.searchParams.get('all') !== '0';

  // People/tags are inherited from the layout; avoid re-running it via parent().
  const { results, totals } = await listTickets({ cookies }, params);

  checkListPage(url, { pageSize, offset }, totals.count);
  return {
    pageSize,
    offset,
    tickets: results,
    totals,
    showAll,
    status,
    search: params.get('search') ?? '',
    priority: params.get('priority') ?? ''
  };
}

export const actions = {
  move: async ({ cookies, request }) => {
    const form = await request.formData();
    const id = String(form.get('id') ?? '');
    const status = String(form.get('status') ?? '');
    const values = { status };
    if (status === 'Closed') values.closed_on = new Date().toISOString().slice(0, 10);
    if (status === 'Resolved')
      values.resolution_note = String(form.get('resolution_note') ?? '').trim();
    try {
      await updateTicket({ cookies }, id, values);
    } catch (err) {
      return fail(400, {
        stageRequirements: stageRequirements(err),
        error: readableError(err, 'Could not move ticket.')
      });
    }
    return { moved: true };
  },
  bulkUpdate: async ({ request, cookies }) => {
    const { ids, fields } = parseBulkForm(await request.formData());
    if (ids.length === 0) return fail(400, { message: 'Select at least one ticket.' });
    const res = await bulkUpdateTickets({ cookies }, ids, fields);
    return { ok: true, kind: 'update', summary: summarizeBulk(res.results) };
  },
  bulkDelete: async ({ request, cookies }) => {
    const ids = (await request.formData()).getAll('ids').map(String);
    if (ids.length === 0) return fail(400, { message: 'Select at least one ticket.' });
    const res = await bulkDeleteTickets({ cookies }, ids);
    return { ok: true, kind: 'delete', summary: summarizeBulk(res.results) };
  }
};
