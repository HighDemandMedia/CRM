import { getCreationSchema, createConfigured } from '$lib/server/v2/creation-forms.js';
import { fail, redirect } from '@sveltejs/kit';
import { createTask, getTaskFormOptions } from '$lib/server/v2/tasks.js';
import { readableError, stageRequirements, fieldErrors } from '$lib/server/v2/form-errors.js';
/** Load only the company and contact choices used by the creation form. */
async function loadOptions(event) {
  const options = await getTaskFormOptions(event);
  return {
    owners: options.owners,
    parents: { contact: options.contacts, account: options.accounts }
  };
}

/**
 * Read the one parent off the form.
 *
 * The form asks "attached to what?" once, a kind and an id, because the
 * model allows exactly one and now says so on every path. Four separate
 * pickers would have let somebody fill two and find out on submit.
 *
 * A chosen kind with no record is an error, not an empty parent. This
 * returned `{}` for that case and the task was created attached to nothing,
 * with a 303 that looked like it had worked, the same silent-success shape
 * the backend audit spent the morning removing. The `required` on the select
 * stops a browser getting here; it is not what makes it true.
 *
 * @param {FormData} form
 * @returns {{ parent?: Record<string, string>, error?: string }}
 */
function readParent(form) {
  const kind = form.get('parent_kind')?.toString() ?? '';
  if (!kind) return { parent: {} };
  const id = form.get(`parent_${kind}`)?.toString() ?? '';
  if (!id) {
    return {
      error: 'Pick which record this is attached to, or set "Attached to" back to Nothing.'
    };
  }
  return { parent: { [kind]: id } };
}

/** @type {import('./$types').Actions} */
export const actions = {
  create: async (event) => {
    const form = await event.request.formData();
    if (form.has('_creation_values')) return createConfigured(event, form, createTask, '/tasks');
    const kind = form.get('parent_kind')?.toString() ?? '';
    const { parent, error: parentError } = readParent(form);

    const values = {
      contacts: [...new Set(form.getAll('contacts').map(String).filter(Boolean))],
      title: form.get('title')?.toString().trim() ?? '',
      status: form.get('status')?.toString() || 'New',
      priority: form.get('priority')?.toString() ?? '',
      // An empty date input submits "", which the API reads as a bad date
      // rather than as "none". Null is the one that means no due date.
      due_date: form.get('due_date')?.toString() || null,
      reminder_days: form.get('reminder_days') ? Number(form.get('reminder_days')) : null,
      description: form.get('description')?.toString().trim() ?? '',
      assigned_to: form
        .getAll('assigned_to')
        .map((v) => v.toString())
        .filter(Boolean),
      ...(parent ?? {})
    };

    if (parentError) {
      return fail(400, { values: { ...values, parent_kind: kind }, error: parentError });
    }

    try {
      await createTask(event, values);
    } catch (/** @type {any} */ err) {
      return fail(400, {
        values: { ...values, parent_kind: kind },
        fieldErrors: fieldErrors(err),
        stageRequirements: stageRequirements(err),
        error: readableError(err, 'Could not save this task.')
      });
    }

    // `TaskListView.post` answers `{error: false, message: ...}` and not the
    // row, so there is no id to redirect to. The list is where the new task
    // is, and it is the page somebody working a queue wants next anyway.
    redirect(303, '/tasks');
  }
};

export async function load(event) {
  const [options, creationSchema] = await Promise.all([
    loadOptions(event),
    getCreationSchema(event, 'Task')
  ]);
  return { ...options, creationSchema };
}
