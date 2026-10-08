import { listPagination, checkListPage } from '$lib/server/v2/pagination.js';
import { readableError, stageRequirements } from '$lib/server/v2/form-errors.js';
import { fail } from '@sveltejs/kit';
import { listTasks, setTaskDone, updateTask } from '$lib/server/v2/tasks.js';
import { taskQuery } from '$lib/server/v2/queue-query.js';
import { getOrgPeopleAndTeams, resolveMe } from '$lib/server/v2/org-people.js';

/**
 * The task queue.
 *
 * `open` is the default view because a task list is a to-do list: the finished
 * ones are history, and history belongs behind a filter rather than at the top
 * of the thing you work from. `?all=1` shows everything, which is the URL the
 * "Show completed" control points at.
 *
 * @type {import('./$types').PageServerLoad}
 */
export async function load(event) {
  const { url, locals } = event;
  const showAll = url.searchParams.get('all') !== '0';

  const params = taskQuery(url);
  const { pageSize, offset } = listPagination(url);
  params.set('limit', String(pageSize));
  params.set('offset', String(offset));

  const [{ results, totals, owners }, orgPeople] = await Promise.all([
    listTasks(event, params),
    getOrgPeopleAndTeams(event.cookies)
  ]);

  checkListPage(url, { pageSize, offset }, totals.count);

  return {
    pageSize,
    offset,
    tasks: results,
    totals,
    owners,
    showAll,
    people: orgPeople.people,
    meId: resolveMe(orgPeople.people, /** @type {any} */ (locals).user?.email),
    canDelete: locals.profile?.role === 'ADMIN'
  };
}

/** @type {import('./$types').Actions} */
export const actions = {
  move: async (event) => {
    const fields = await event.request.formData();
    const id = String(fields.get('id') ?? '');
    const status = String(fields.get('status') ?? '');
    if (!id || !status) return fail(400, { error: 'Invalid task status.' });
    try {
      await updateTask(event, id, { status });
    } catch (err) {
      return fail(400, {
        stageRequirements: stageRequirements(err),
        error: readableError(err, 'Could not move the task. Please try again.')
      });
    }
    return { saved: true };
  },
  /**
   * Tick a row off, or put it back.
   *
   * The mock did this in local state with a note saying it must never look
   * saved without being saved. This is that PATCH: the row reverts on failure
   * because the page reloads from the API either way.
   */
  toggle: async (event) => {
    const form = await event.request.formData();
    const id = form.get('id')?.toString();
    const done = form.get('done')?.toString() === 'true';
    if (!id) return fail(400, { error: 'Which task?' });

    try {
      await setTaskDone(event, id, done);
    } catch (/** @type {any} */ err) {
      // 403 is the interesting one: the list can show a task you may read
      // through a shared parent but not edit.
      return fail(err?.status === 403 ? 403 : 400, {
        error:
          err?.status === 403
            ? 'That task is not yours to change.'
            : (err?.body?.errors ?? 'That did not save. Try again.')
      });
    }
    return { done };
  }
};
