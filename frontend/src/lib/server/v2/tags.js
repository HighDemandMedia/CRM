/** Active tag lookups remain available to record forms; Settings catalogs require access. */
import { apiRequest } from '$lib/api-helpers.js';
import { viewerRole } from './organization.js';

/**
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @returns {Promise<{ tags: any[], totals: any, can_edit: boolean }>}
 */
export async function getTags({ cookies }, { includeArchived = false } = {}) {
  const resp = await apiRequest(
    includeArchived ? '/tags/?include_archived=true' : '/tags/',
    {},
    { cookies }
  );
  return {
    tags: resp.tags ?? [],
    totals: resp.totals ?? { count: 0, active: 0, unused: 0 },
    can_edit: viewerRole(cookies) === 'ADMIN'
  };
}

/**
 * Create a tag.
 *
 * Only `name` and an optional `color` are sent. `org` comes from the JWT on the backend, and `usage`
 * and `totals` are computed, never submitted. The empty-name guard is a fast
 * fail for an obvious mistake, not a security control: `TagsListView.post`
 * (`backend/common/views/tags_views.py`) runs its own `if not name:` check
 * after stripping the param, and that is the real authority. `TagsSerializer`
 * is not in this path at all; the view only uses it to shape the response.
 *
 * `TagsListView.post` wraps its result in an envelope,
 * `{ error, message, tag }`, on both the create branch and the reactivation
 * branch (an archived tag with the same slug is revived instead of
 * duplicated). This unwraps to `.tag` deliberately rather than just fixing
 * the doc comment: a function named `createTag` that resolves to the
 * envelope is a trap the next caller will fall into blind, exactly like
 * `createLead` does today, `LeadListView.post` returns no id at all, so
 * `leads/new/+page.server.js`'s `created?.id` is always undefined and every
 * lead creation redirects to `/leads` instead of the new record. Not every
 * create endpoint in this codebase gives you a record back; the seven
 * settings pages that copy this function will want to link to or highlight
 * the tag they just made, so this one hands back the real thing.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {{ name?: string, [key: string]: any }} values callers may pass extra
 *   keys (a hostile `org`, say); the index signature lets TypeScript accept
 *   the object literal without widening what this function actually reads,
 *   which stays `name` and optional `color`.
 * @returns {Promise<any>} the created (or reactivated) tag record: `{ id, name,
 *   slug, color, description, is_active, created_at }`.
 */
export async function createTag({ cookies }, values) {
  const name = (values.name ?? '').trim();
  if (!name) throw new Error('A tag needs a name.');

  const body = values.color ? { name, color: values.color } : { name };
  const resp = await apiRequest('/tags/', { method: 'POST', body }, { cookies });
  return resp.tag ?? resp;
}

/**
 * Archive a tag.
 *
 * This is a soft delete and the copy around it must say so. `TagsDetailView`
 * sets `is_active = False`, saves, and returns 200 with
 * `{ error: false, message: 'Tag archived successfully' }`. It never calls
 * `.delete()`, no hard-delete path is exposed anywhere, and every relationship
 * to a tag from a taggable model is a ManyToManyField, so nothing is cascaded
 * or protected. The rows that carry the tag keep it; the tag simply stops being
 * offered. `restoreTag` puts it back.
 *
 * Admin-only on the backend, 403 otherwise. The page hides the control for a
 * member using the `can_edit` hint from `getTags`, but that hint is decoded
 * from the JWT and is display only; the backend re-derives the role and is the
 * check that matters.
 *
 * No body is sent: the tag is identified by the URL and the backend derives
 * org and actor from the token.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {string} id
 * @returns {Promise<any>}
 */
export async function archiveTag({ cookies }, id) {
  if (!id) throw new Error('A tag id is required to turn a tag off.');
  return await apiRequest(`/tags/${id}/`, { method: 'DELETE' }, { cookies });
}

/**
 * Restore an archived tag: sets `is_active = True` again. Admin-only, 200 on
 * success. The list already includes archived tags (`?include_archived=true`),
 * so a restored tag needs no separate fetch to become visible.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {string} id
 * @returns {Promise<any>}
 */
export async function restoreTag({ cookies }, id) {
  if (!id) throw new Error('A tag id is required to turn a tag back on.');
  return await apiRequest(`/tags/${id}/restore/`, { method: 'POST' }, { cookies });
}

/**
 * Merge `id` into `into`: every record in the org carrying `id` gets `into`
 * instead, and `id` is archived.
 *
 * Only the two ids are sent. Both are resolved inside the caller's org by
 * `TagsMergeView`, which is the check that matters: `into` arrives in a
 * request body, so an unscoped lookup there would let an admin stamp another
 * tenant's tag onto their own records. Admin-only, 403 otherwise, the same
 * split as `createTag` and `archiveTag`.
 *
 * This is not reversible by re-running it the other way. The source is
 * archived rather than deleted, so the name survives and `restoreTag` brings
 * it back, but the records have moved and nothing remembers which ones came
 * from where. The page confirms before submitting for that reason.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {string} id the tag to empty out
 * @param {string} into the tag to keep
 * @returns {Promise<{ tag: any, moved: number }>} the surviving tag and how
 *   many records changed hands, which is what the page reports back.
 */
export async function mergeTags({ cookies }, id, into) {
  if (!id || !into) throw new Error('Two tags are required to merge.');
  const resp = await apiRequest(
    `/tags/${id}/merge/`,
    { method: 'POST', body: { into } },
    { cookies }
  );
  return { tag: resp.tag ?? null, moved: resp.moved ?? 0 };
}

/** Update the tag itself so its existing record associations keep the same ID. */
export async function updateTag({ cookies }, id, values) {
  const name = (values.name ?? '').trim();
  if (!id || !name) throw new Error('A tag needs a name.');
  const response = await apiRequest(
    `/tags/${id}/`,
    {
      method: 'PUT',
      body: { name, color: values.color }
    },
    { cookies }
  );
  return response.tag ?? response;
}
