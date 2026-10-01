import { fail } from '@sveltejs/kit';
import { getTaskFormOptions, updateTask } from '$lib/server/v2/tasks.js';
import { readableError, stageRequirements } from '$lib/server/v2/form-errors.js';
import { listTickets } from '$lib/server/v2/tickets.js';
import { listDeals } from '$lib/server/v2/deals.js';

export async function getTaskEditor(event, task) {
  const [options, tickets, deals] = await Promise.allSettled([
    getTaskFormOptions(event),
    listTickets(event, new URLSearchParams({ limit: '100' })),
    // Open deals only, matching what this picker offered before `listDeals`
    // stopped assuming it: attaching a task to a deal you already closed is
    // an edge case the picker does not need to carry by default.
    listDeals(event, new URLSearchParams({ open: 'true', limit: '100' }))
  ]);
  const settled = options.status === 'fulfilled' ? options.value : { owners: [], accounts: [] };

  return {
    task,
    owners: settled.owners,
    parents: {
      account: settled.accounts ?? [],
      opportunity:
        deals.status === 'fulfilled'
          ? deals.value.results.map((/** @type {any} */ d) => ({ id: d.id, name: d.name }))
          : [],
      case:
        tickets.status === 'fulfilled'
          ? tickets.value.results.map((/** @type {any} */ t) => ({ id: t.id, name: t.name }))
          : []
    },
    form: {
      title: task.title,
      status: task.status,
      priority: task.priority,
      due_date: task.due_date ?? '',
      reminder_days: task.reminder_days ?? '',
      description: task.description,
      // `related.kind` is the v2 word; the API columns are the other four.
      parent_kind: task.related
        ? { account: 'account', deal: 'opportunity', ticket: 'case', lead: 'lead' }[
            task.related.kind
          ]
        : '',
      parent_id: task.related?.id ?? ''
    }
  };
}

export async function saveTaskEditor(event) {
  const form = await event.request.formData();

  /** @type {Record<string, any>} */
  const values = {
    title: form.get('title')?.toString().trim() ?? '',
    status: form.get('status')?.toString() || 'New',
    priority: form.get('priority')?.toString() ?? '',
    due_date: form.get('due_date')?.toString() || null,
    reminder_days: form.get('reminder_days') ? Number(form.get('reminder_days')) : null,
    description: form.get('description')?.toString().trim() ?? '',
    assigned_to: form
      .getAll('assigned_to')
      .map((v) => v.toString())
      .filter(Boolean)
  };

  /*
   * The parent is only sent when it actually moved.
   *
   * Same "absent means unchanged" marker as the other modules, and here it
   * guards a validation rule rather than a relation: the API checks the
   * payload's parents *against the ones already on the task*, so re-sending
   * an unchanged account alongside nothing else is fine, but the moment the
   * kind changes both columns have to travel together, the old one cleared
   * to null in the same request as the new one is set. Sent one at a time
   * they read as "a second parent" and are refused, which is the rule
   * working.
   */
  const kind = form.get('parent_kind')?.toString() ?? '';
  const id = kind ? (form.get(`parent_${kind}`)?.toString() ?? '') : '';
  const kindWas = form.get('parent_kind_original')?.toString() ?? '';
  const idWas = form.get('parent_id_original')?.toString() ?? '';

  if (kind !== kindWas || id !== idWas) {
    if (kindWas) values[kindWas] = null;
    if (kind && id) values[kind] = id;
  }

  try {
    await updateTask(event, event.params.id, values);
  } catch (/** @type {any} */ err) {
    return fail(400, {
      values: { ...values, parent_kind: kind, parent_id: id },
      stageRequirements: stageRequirements(err),
      error: readableError(err, 'Could not save this task.')
    });
  }

  return { saved: true };
}
