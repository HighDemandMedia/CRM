import { getOrgPeopleAndTeams, resolveMe } from '$lib/server/v2/org-people.js';
import { apiRequest } from '$lib/api-helpers.js';
import { createContactTag, readContactTags } from '$lib/server/v2/contact-tags.js';
import { fail } from '@sveltejs/kit';
import { readableError, stageRequirements, fieldErrors } from '$lib/server/v2/form-errors.js';
import {
  getAccount,
  getAccountForEdit,
  updateAccount,
  EDITABLE_FIELDS,
  addCompanyAttachment
} from '$lib/server/v2/accounts.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies, params, locals }) {
  const [account, editor, { people }] = await Promise.all([
    getAccount({ cookies }, params.id),
    getAccountForEdit({ cookies }, params.id),
    getOrgPeopleAndTeams(cookies)
  ]);
  return { ...account, editor, hosts: people, defaultHost: resolveMe(people, locals.user?.email) };
}

/** @type {import('./$types').Actions} */
export const actions = {
  note: async ({ cookies, params, request }) => {
    const form = await request.formData();
    const comment = String(form.get('comment') ?? '').trim();
    if (!comment) return fail(400, { message: 'Write a note before saving.' });
    try {
      await apiRequest(`/accounts/${params.id}/`, { method: 'POST', body: { comment } }, { cookies });
      return { noted: true };
    } catch (err) {
      return fail(400, { message: readableError(err, 'Could not save note.') });
    }
  },
  association: async ({ cookies, params, request }) => {
    const form = await request.formData();
    try {
      await apiRequest(
        `/record-associations/company/${params.id}/`,
        {
          method: 'POST',
          body: Object.fromEntries(
            ['kind', 'operation', 'target'].map((k) => [k, String(form.get(k) ?? '')])
          )
        },
        { cookies }
      );
      return { associated: true };
    } catch (err) {
      return fail(400, { message: String(err?.message || 'Could not update association.') });
    }
  },
  createTag: createContactTag,
  save: async ({ cookies, params, request }) => {
    const form = await request.formData();

    /** @type {Record<string, any>} */
    const values = {};
    readContactTags(form, values);
    if (form.has('contacts_present')) {
      const ids = form.getAll('contacts').map(String).sort();
      if (JSON.stringify(ids) !== form.get('contacts_original')) values.contacts = ids;
    }

    for (const field of EDITABLE_FIELDS) {
      // Only fields the form actually submitted. A control that is absent or
      // disabled sends nothing, and "nothing" is how PATCH is told to leave a
      // field alone. See `updateAccount`.
      if (form.has(field)) values[field] = form.get(field)?.toString().trim() ?? '';
    }

    /*
     * The owner is only sent when somebody actually changed it.
     *
     * `assigned_to` is many-to-many and this form offers a single select, so
     * sending it unconditionally rewrites the whole list from one value, an
     * account with two people on it silently loses one every time anybody
     * edits the phone number. The hidden `assigned_to_original` is what makes
     * "nobody touched this" distinguishable from "somebody chose this".
     */
    const owner = form.get('assigned_to')?.toString().trim() ?? '';
    const ownerWas = form.get('assigned_to_original')?.toString().trim() ?? '';
    if (form.has('assigned_to') && owner !== ownerWas) values.assigned_to = owner;

    try {
      await updateAccount({ cookies }, params.id, values);
    } catch (/** @type {any} */ err) {
      return fail(400, { values, fieldErrors: fieldErrors(err), stageRequirements: stageRequirements(err), error: readableError(err, 'Could not save this company.') });
    }

    return { saved: true };
  },
  saveFields: async ({ cookies, params, request }) => {
    try {
      const form = await request.formData();
      const changes = JSON.parse(String(form.get('changes') ?? '{}'));
      if (!changes || Array.isArray(changes) || typeof changes !== 'object')
        return fail(400, { error: 'Invalid changes.' });
      const allowed = new Set([...EDITABLE_FIELDS, 'contacts', 'assigned_to', 'tags']);
      if (Object.keys(changes).some((key) => !allowed.has(key)))
        return fail(400, { error: 'Invalid property.' });
      if (Object.keys(changes).length) await updateAccount({ cookies }, params.id, changes);
      return { saved: true };
    } catch (/** @type {any} */ err) {
      return fail(400, { fieldErrors: fieldErrors(err), stageRequirements: stageRequirements(err), error: readableError(err, 'Could not save changes.') });
    }
  },
  attach: async ({ cookies, params, request }) => {
    const form = await request.formData();
    const file = form.get('attachment');
    if (!file || typeof file === 'string' || !file.size)
      return fail(400, { message: 'Choose a file to attach.' });
    try {
      await addCompanyAttachment({ cookies }, params.id, file);
    } catch (/** @type {any} */ err) {
      return fail(400, { message: readableError(err, 'Could not attach file.') });
    }
    return { attached: true };
  }
};
