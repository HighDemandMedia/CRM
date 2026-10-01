import { createContactTag, readContactTags } from '$lib/server/v2/contact-tags.js';
import { fail, redirect } from '@sveltejs/kit';
import { EDITABLE_FIELDS, createContact, getContactFormOptions } from '$lib/server/v2/contacts.js';
import { readableError, stageRequirements, fieldErrors } from '$lib/server/v2/form-errors.js';

/**
 * `?account=<id>` preselects the company, so "add somebody at this account"
 * arrives with the account already chosen. An id that is not one of this org's
 * accounts is dropped rather than trusted. The picker is built from the API's
 * own list, and the serializer checks the org again on save.
 *
 * @type {import('./$types').PageServerLoad}
 */
export async function load({ cookies, url }) {
  return await getContactFormOptions({ cookies }, url.searchParams.get('account'));
}

/** @type {import('./$types').Actions} */
export const actions = {
  createTag: createContactTag,
  create: async ({ cookies, request }) => {
    const form = await request.formData();

    /** @type {Record<string, any>} */
    const values = {};
    readContactTags(form, values);
    for (const field of EDITABLE_FIELDS) {
      if (field === 'is_active') continue;
      if (form.has(field)) values[field] = form.get(field)?.toString().trim() ?? '';
    }
    // On create there is nothing to preserve, so the owner is always sent,
    // including empty, which is how a contact is deliberately left unowned.
    values.assigned_to = form.get('assigned_to')?.toString().trim() ?? '';

    /** @type {any} */
    let created;
    try {
      created = await createContact({ cookies }, values);
    } catch (/** @type {any} */ err) {
      return fail(400, {
        values,
        fieldErrors: fieldErrors(err),
        stageRequirements: stageRequirements(err),
        error: readableError(err, 'Could not create this contact.')
      });
    }

    // The API returns the new id. Landing on the person is the point of adding
    // one; landing back on the list makes you go and find them.
    redirect(303, created?.id ? `/contacts/${created.id}` : '/contacts');
  }
};
