import { fail } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { getOrgPeopleAndTeams, resolveMe } from '$lib/server/v2/org-people.js';
import { readableError } from '$lib/server/v2/form-errors.js';
export async function load({ cookies, locals }) {
  const { people } = await getOrgPeopleAndTeams(cookies);
  return { hosts: people, defaultHost: resolveMe(people, locals.user?.email) };
}
export const actions = {
  manage: async ({ cookies, request }) => {
    const form = await request.formData();
    const [kind, id] = String(form.get('event_id') ?? '').split(':');
    const operation = String(form.get('operation') ?? '');
    if (
      !['appointment', 'contact', 'company'].includes(kind) ||
      !/^[0-9a-f-]{36}$/i.test(id ?? '') ||
      !['cancel', 'reschedule'].includes(operation)
    )
      return fail(400, { message: 'Invalid event action.' });
    const start = String(form.get('starts_at') ?? '');
    const end = String(form.get('ends_at') ?? '');
    if (
      operation === 'reschedule' &&
      (!Number.isFinite(Date.parse(start)) ||
        (kind === 'appointment' &&
          (!Number.isFinite(Date.parse(end)) || Date.parse(end) <= Date.parse(start))))
    )
      return fail(400, { message: 'Choose a valid date and time.' });
    try {
      if (kind === 'appointment')
        await apiRequest(
          `/sales-appointments/${id}/`,
          { method: 'PATCH', body: { operation, starts_at: start, ends_at: end } },
          { cookies }
        );
      else
        await apiRequest(
          `/${kind === 'contact' ? 'contacts' : 'accounts'}/${id}/`,
          { method: 'PATCH', body: { appointment_at: operation === 'cancel' ? null : start } },
          { cookies }
        );
      return { saved: true };
    } catch (err) {
      return fail(400, { message: readableError(err, 'Could not update event.') });
    }
  },
  create: async ({ cookies, request }) => {
    const form = await request.formData();
    const body = Object.fromEntries(
      ['title', 'host', 'starts_at', 'ends_at', 'internal_notes'].map((key) => [
        key,
        String(form.get(key) ?? '')
      ])
    );
    const attendee = String(form.get('attendee') ?? '');
    if (attendee) {
      const [kind, id] = attendee.split(':');
      if (!['contact', 'company'].includes(kind) || !id)
        return fail(400, { message: 'Select a valid attendee.' });
      body[kind] = id;
    }
    try {
      await apiRequest('/sales-appointments/', { method: 'POST', body }, { cookies });
      return { created: true };
    } catch (err) {
      return fail(400, { message: readableError(err, 'Could not schedule event.') });
    }
  }
};
