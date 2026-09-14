import { createContactTag, readContactTags } from '$lib/server/v2/contact-tags.js';
import { fail, redirect } from '@sveltejs/kit';
import { EDITABLE_FIELDS, createAccount, getAccountFormOptions } from '$lib/server/v2/accounts.js';
import { readableError } from '$lib/server/v2/form-errors.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies }) {
  return await getAccountFormOptions({ cookies });
}

/** @type {import('./$types').Actions} */
export const actions = {
  createTag: createContactTag,
  create: async ({ cookies, request }) => {
    const form = await request.formData();

    /** @type {Record<string, any>} */
    const values = {};
    readContactTags(form, values);
    if (form.has('assigned_to')) values.assigned_to = String(form.get('assigned_to') ?? '');
    if (form.has('contacts_present')) {
      const ids = form.getAll('contacts').map(String).sort();
      if (JSON.stringify(ids) !== form.get('contacts_original')) values.contacts = ids;
    }

    for (const field of EDITABLE_FIELDS) {
      if (form.has(field)) values[field] = form.get(field)?.toString().trim() ?? '';
    }
    /** @type {any} */
    let created;
    try {
      created = await createAccount({ cookies }, values);
    } catch (/** @type {any} */ err) {
      return fail(400, { values, error: readableError(err, 'Could not create this company.') });
    }

    // The API returns the new id. Landing on the account is the point of
    // creating one; landing back on the list makes you go and find it.
    redirect(303, created?.id ? `/accounts/${created.id}` : '/accounts');
  }
};
