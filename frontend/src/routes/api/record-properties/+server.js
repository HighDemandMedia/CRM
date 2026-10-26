import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { readableError, fieldErrors, stageRequirements } from '$lib/server/v2/form-errors.js';
import { updateContact, EDITABLE_FIELDS as contactFields } from '$lib/server/v2/contacts.js';
import { updateAccount, EDITABLE_FIELDS as accountFields } from '$lib/server/v2/accounts.js';
const endpoints = {
  Contact: 'contacts',
  Account: 'accounts',
  Opportunity: 'opportunities',
  Task: 'tasks',
  Case: 'cases'
};
const systemEditors = {
  Contact: { update: updateContact, fields: contactFields },
  Account: { update: updateAccount, fields: accountFields }
};
export async function POST({ cookies, request }) {
  let input;
  try {
    input = await request.json();
  } catch {
    return json({ error: 'Invalid properties.' }, { status: 400 });
  }
  const { target, id, values, system = false } = input ?? {};
  if (
    !Object.hasOwn(endpoints, target) ||
    !/^[0-9a-f-]{36}$/i.test(id) ||
    !values ||
    typeof values !== 'object' ||
    Array.isArray(values) ||
    !Object.keys(values).length
  )
    return json({ error: 'Invalid properties.' }, { status: 400 });
  const editor = Object.hasOwn(systemEditors, target) ? systemEditors[target] : null;
  if (
    system &&
    (!editor ||
      Object.keys(values).some((key) => ![...editor.fields, 'assigned_to', 'tags'].includes(key)))
  )
    return json({ error: 'Invalid property.' }, { status: 400 });
  try {
    // Reuse existing PATCH adapters; the API authorizes the tenant, record and changed fields.
    if (system) await editor.update({ cookies }, id, values);
    else
      await apiRequest(
        `/${endpoints[target]}/${id}/`,
        { method: 'PATCH', body: { custom_fields: values } },
        { cookies }
      );
    return json({ saved: true });
  } catch (err) {
    return json(
      {
        error: readableError(err, 'Could not save the property.'),
        fieldErrors: fieldErrors(err),
        stageRequirements: stageRequirements(err)
      },
      { status: err.status || 400 }
    );
  }
}
