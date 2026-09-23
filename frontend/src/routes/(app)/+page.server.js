import { apiRequest } from '$lib/api-helpers.js';
import { fail } from '@sveltejs/kit';
import { setTaskDone } from '$lib/server/v2/tasks.js';
import { actions as calendarActions } from './calendar/+page.server.js';
export async function load({ cookies, url }) {
  const params = new URLSearchParams();
  if (url.searchParams.get('user')) params.set('user', url.searchParams.get('user'));
  return { day: await apiRequest(`/dashboard/day-summary/?${params}`, {}, { cookies }) };
}
export const actions = {
  manage: ({ cookies, request }) =>
    calendarActions.manage(/** @type {any} */ ({ cookies, request })),
  complete: async (event) => {
    const form = await event.request.formData();
    const id = String(form.get('id') ?? '');
    if (!id) return fail(400, { error: 'Choose a task.' });
    try {
      await setTaskDone(event, id, true);
    } catch {
      return fail(400, { error: 'Could not complete the task. Please try again.' });
    }
    return { saved: true };
  }
};
