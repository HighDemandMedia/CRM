import { apiRequest } from '$lib/api-helpers.js';
import { readableError } from '$lib/server/v2/form-errors.js';
import { fail } from '@sveltejs/kit';
import {
  getNotifications,
  markNotificationRead,
  markAllNotificationsRead
} from '$lib/server/v2/notifications.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies, url }) {
  const [feed, preferences] = await Promise.all([getNotifications({ cookies, url }), apiRequest('/profile/', {}, { cookies })]);
  return { ...feed, preferences };
}

/** @type {import('./$types').Actions} */
export const actions = {
  preferences: async ({ cookies, request }) => {
    const form = await request.formData();
    const body = Object.fromEntries(['notify_in_app', 'notify_mentions', 'notify_comments'].map(key => [key, form.get(key) === 'on']));
    try {
      await apiRequest('/profile/', { method: 'PATCH', body }, { cookies });
      return { scope: 'preferences', saved: true };
    } catch (err) { return fail(400, { scope: 'preferences', message: readableError(err, 'Could not save preferences.') }); }
  },

  /**
   * Mark one notification read. The page updates optimistically and calls this
   * to persist; `markNotificationRead` hits the recipient-scoped endpoint, so a
   * forged id for someone else's notification is a 404 there, not a write.
   */
  read: async ({ cookies, request }) => {
    const form = await request.formData();
    const id = form.get('id')?.toString() ?? '';
    if (!id) return fail(400, { error: 'Missing notification id.' });

    try {
      await markNotificationRead({ cookies }, id);
    } catch (/** @type {any} */ err) {
      return fail(err?.status === 404 ? 404 : 500, { error: 'Could not mark that read.' });
    }
    return { ok: true };
  },

  /** Mark every unread notification read. */
  readAll: async ({ cookies }) => {
    try {
      await markAllNotificationsRead({ cookies });
    } catch {
      return fail(500, { error: 'Could not mark everything read.' });
    }
    return { ok: true };
  }
};
