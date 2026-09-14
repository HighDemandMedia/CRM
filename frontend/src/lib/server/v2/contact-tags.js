import { fail } from '@sveltejs/kit';
import { createTag } from './tags.js';
import { readableError } from './form-errors.js';

/** @param {any} event */
export async function createContactTag(event) {
  const form = await event.request.formData();
  try {
    const tag = await createTag(event, {
      name: String(form.get('name') ?? ''),
      color: String(form.get('color') ?? 'blue')
    });
    return { tag };
  } catch (/** @type {any} */ err) {
    return fail(400, { error: readableError(err, 'Could not create tag.') });
  }
}

/** @param {FormData} form @param {Record<string, any>} values */
export function readContactTags(form, values) {
  if (!form.has('tags_present')) return;
  const tags = form.getAll('tags').map(String).sort();
  if (JSON.stringify(tags) !== form.get('tags_original')) values.tags = tags;
}
