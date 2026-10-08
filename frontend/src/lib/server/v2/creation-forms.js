import { apiRequest } from '$lib/api-helpers.js';
import { fail, redirect } from '@sveltejs/kit';
import { fieldErrors, readableError, stageRequirements } from './form-errors.js';

export const creationObjects = [
  { value: 'Contact', label: 'Contacts' },
  { value: 'Account', label: 'Companies' },
  { value: 'Opportunity', label: 'Deals' },
  { value: 'Task', label: 'Tasks' },
  { value: 'Case', label: 'Tickets' }
];
export function getCreationSchema(event, target) {
  return apiRequest(`/creation-forms/${target}/`, {}, event);
}

/** A configured form uses existing create adapters and their explicit allowlists. */
export async function createConfigured(event, form, create, path) {
  let values;
  try {
    values = JSON.parse(String(form.get('_creation_values')));
    if (!values || typeof values !== 'object' || Array.isArray(values))
      throw new Error('Invalid form values.');
  } catch {
    return fail(400, {
      error: 'Could not read the form. Reload and try again.',
      values: {},
      fieldErrors: {},
      stageRequirements: null
    });
  }
  let created;
  try {
    created = await create(event, values);
  } catch (error) {
    const target = {
      '/contacts': 'Contact',
      '/accounts': 'Account',
      '/pipeline': 'Opportunity',
      '/tasks': 'Task',
      '/tickets': 'Case'
    }[path];
    // Refresh after rejection so an administrator's newly required fields are actionable.
    const creationSchema = target ? await getCreationSchema(event, target).catch(() => null) : null;
    return fail(error?.status === 403 ? 403 : 400, {
      values,
      creationSchema,
      fieldErrors: {
        ...fieldErrors(error),
        ...Object.fromEntries(
          Object.entries(error?.body?.errors?.custom_fields ?? {}).map(([key, value]) => [
            'custom_fields.' + key,
            Array.isArray(value) ? value.join(' ') : String(value)
          ])
        )
      },
      stageRequirements: stageRequirements(error),
      error: readableError(error, 'Could not create this record.')
    });
  }
  redirect(303, created?.id ? `${path}/${created.id}` : path);
}
