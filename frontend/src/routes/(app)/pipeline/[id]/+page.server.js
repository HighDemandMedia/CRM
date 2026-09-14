import { fail } from '@sveltejs/kit';
import {
  getDeal,
  addDealAttachment,
  addDealNote,
  getDealForEdit,
  updateDeal,
  EDITABLE_FIELDS
} from '$lib/server/v2/deals.js';
import { readableError } from '$lib/server/v2/form-errors.js';
/** @type {import('./$types').PageServerLoad} */
export async function load(event) {
  const [deal, editor] = await Promise.all([
    getDeal(event, event.params.id),
    getDealForEdit(event, event.params.id)
  ]);
  return { ...deal, editor };
}
/** @type {import('./$types').Actions} */
export const actions = {
  async save(event) {
    const form = await event.request.formData();

    /**
     * Only fields the form actually submitted. A disabled input sends nothing,
     * and PATCH reads absent as "leave this alone", which is exactly right
     * for the amount on a deal whose line items own it.
     * @type {Record<string, any>}
     */
    const values = {};
    if (form.has('contacts_present')) {
      const ids = form.getAll('contacts').map(String).sort();
      if (JSON.stringify(ids) !== form.get('contacts_original')) values.contacts = ids;
    }
    for (const field of EDITABLE_FIELDS) {
      if (form.has(field)) values[field] = form.get(field)?.toString().trim() ?? '';
    }

    /*
     * The owner is only sent when somebody actually changed it.
     *
     * `assigned_to` is many-to-many and this form offers a single select, so
     * sending it unconditionally rewrites the whole list from one value,
     * a deal with two people on it silently loses one every time anybody
     * edits the description. Caught by saving a real two-assignee deal and
     * counting the assignees afterwards.
     *
     * Comparing against the value the form was rendered with keeps "nobody
     * touched this" distinguishable from "somebody chose this", which is the
     * distinction PATCH is built on.
     */
    const owner = form.get('assigned_to')?.toString().trim() ?? '';
    const ownerWas = form.get('assigned_to_original')?.toString().trim() ?? '';
    if (owner !== ownerWas) values.assigned_to = owner;

    try {
      await updateDeal(event, event.params.id, values);
    } catch (/** @type {any} */ err) {
      // The API's field errors are the ones that count: this form's own
      // checks are a UX hint and the serializer is the rule.
      return fail(400, { values, error: String(err?.message ?? 'Could not save the deal.') });
    }

    return { saved: true };
  },
  note: async (event) => {
    const form = await event.request.formData();
    const comment = String(form.get('comment') ?? '').trim();
    if (!comment) return fail(400, { message: 'Write a note before saving.' });
    try {
      await addDealNote(event, event.params.id, comment);
      return { noted: true };
    } catch (/** @type {any} */ err) {
      return fail(400, { message: readableError(err, 'Could not save note.') });
    }
  },
  attach: async (event) => {
    const form = await event.request.formData(),
      file = form.get('attachment');
    if (!file || typeof file === 'string' || !file.size)
      return fail(400, { message: 'Choose a file to attach.' });
    try {
      await addDealAttachment(event, event.params.id, file);
      return { attached: true };
    } catch (/** @type {any} */ err) {
      return fail(400, { message: readableError(err, 'Could not attach file.') });
    }
  },
  saveFields: async (event) => {
    try {
      const form = await event.request.formData();
      const changes = JSON.parse(String(form.get('changes') ?? '{}'));
      if (!changes || Array.isArray(changes) || typeof changes !== 'object')
        return fail(400, { error: 'Invalid changes.' });
      const allowed = new Set([...EDITABLE_FIELDS, 'assigned_to', 'contacts']);
      if (Object.keys(changes).some((key) => !allowed.has(key)))
        return fail(400, { error: 'Invalid property.' });
      if (Object.keys(changes).length) await updateDeal(event, event.params.id, changes);
      return { saved: true };
    } catch (/** @type {any} */ err) {
      return fail(400, { error: readableError(err, 'Could not save changes.') });
    }
  }
};
