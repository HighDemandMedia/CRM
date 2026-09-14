import { getOrgPeopleAndTeams, resolveMe } from '$lib/server/v2/org-people.js';
import { createContactTag, readContactTags } from '$lib/server/v2/contact-tags.js';
import { readableError } from '$lib/server/v2/form-errors.js';
import { fail } from '@sveltejs/kit';
import {
  addContactNote,
  getContact,
  updateContact,
  EDITABLE_FIELDS
} from '$lib/server/v2/contacts.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies, params, locals }) {
  const [contact, { people }] = await Promise.all([
    getContact({ cookies }, params.id, true),
    getOrgPeopleAndTeams(cookies)
  ]);
  return { ...contact, hosts: people, defaultHost: resolveMe(people, locals.user?.email) };
}

const FLAGS = ['do_not_call', 'is_active'];
/** @type {import('./$types').Actions} */
export const actions = {
  save: async ({ cookies, params, request }) => {
    const form = await request.formData();

    /** @type {Record<string, any>} */
    const values = {};
    readContactTags(form, values);
    for (const field of EDITABLE_FIELDS) {
      if (FLAGS.includes(field)) continue;
      // Only fields the form actually submitted. A control that is absent or
      // disabled sends nothing, and "nothing" is how PATCH is told to leave a
      // field alone. See `updateContact`.
      if (form.has(field)) values[field] = form.get(field)?.toString().trim() ?? '';
    }

    /*
     * A cleared checkbox submits nothing at all, so "absent means leave alone"
     * is exactly wrong for these two: it would make "do not call" impossible to
     * switch off. Each one is paired with a hidden field that is always sent,
     * so the form can distinguish an unticked box from a field it does not own.
     */
    for (const flag of FLAGS) {
      if (form.has(`${flag}_present`)) values[flag] = form.get(flag) === 'on';
    }

    /*
     * The owner is only sent when somebody actually changed it.
     *
     * `assigned_to` is many-to-many and this form offers a single select, so
     * sending it unconditionally rewrites the whole list from one value, a
     * contact with two people on it silently loses one every time anybody edits
     * a phone number. The hidden `assigned_to_original` is what makes "nobody
     * touched this" distinguishable from "somebody chose this".
     */
    const owner = form.get('assigned_to')?.toString().trim() ?? '';
    const ownerWas = form.get('assigned_to_original')?.toString().trim() ?? '';
    if (owner !== ownerWas) values.assigned_to = owner;

    try {
      await updateContact({ cookies }, params.id, values);
    } catch (/** @type {any} */ err) {
      return fail(400, { values, error: readableError(err, 'Could not save this contact.') });
    }

    return { saved: true };
  },
  createTag: createContactTag,
  saveFields: async ({ cookies, params, request }) => {
    const form = await request.formData();
    try {
      const submitted = JSON.parse(String(form.get('changes') ?? '{}'));
      if (!submitted || typeof submitted !== 'object' || Array.isArray(submitted))
        return fail(400, { error: 'Invalid contact changes.' });
      const values = Object.fromEntries(
        Object.entries(submitted).filter(([key]) =>
          [...EDITABLE_FIELDS, 'assigned_to', 'tags'].includes(key)
        )
      );
      if (
        'tags' in values &&
        (!Array.isArray(values.tags) || values.tags.some((id) => typeof id !== 'string'))
      )
        return fail(400, { error: 'Invalid tags.' });
      if (Object.keys(values).length) await updateContact({ cookies }, params.id, values);
      return { saved: true };
    } catch (/** @type {any} */ err) {
      return fail(400, { error: readableError(err, 'Could not save contact changes.') });
    }
  },
  /**
   * Log a note against the contact, with an optional file. The body carries only
   * the note text and the file; who wrote it and which org it belongs to are
   * derived server-side from the JWT (see `addContactNote`), never from the form.
   *
   * A contact accepts a file on its own, unlike a lead, `ContactDetailView.post`
   * saves the attachment in a separate block from the comment, so this refuses
   * only the empty case: nothing typed and nothing picked. The DRF view enforces
   * the same access as reading the contact, so this action cannot post to a
   * contact the caller could not open.
   */
  note: async ({ cookies, params, request }) => {
    const form = await request.formData();
    const comment = form.get('comment')?.toString().trim() ?? '';

    const picked = form.get('attachment');
    const file =
      picked && typeof picked === 'object' && 'size' in picked && picked.size > 0 ? picked : null;

    if (!comment && !file) {
      return fail(400, { message: 'Write a note or attach a file before you save.' });
    }

    try {
      await addContactNote({ cookies }, params.id, comment, file);
    } catch (/** @type {any} */ err) {
      return fail(400, { message: String(err?.message ?? 'Could not save that note.') });
    }

    return { noted: true };
  }
};
