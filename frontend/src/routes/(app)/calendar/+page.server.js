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
      !['appointment', 'contact', 'company', 'google'].includes(kind) ||
      !/^[0-9a-f-]{36}$/i.test(id ?? '') ||
      !['cancel', 'reschedule', 'details'].includes(operation)
    )
      return fail(400, { message: 'Invalid event action.' });
    const start = String(form.get('starts_at') ?? '');
    const end = String(form.get('ends_at') ?? '');
    if (
      operation === 'reschedule' &&
      (!Number.isFinite(Date.parse(start)) ||
        (['appointment', 'google'].includes(kind) &&
          (!Number.isFinite(Date.parse(end)) || Date.parse(end) <= Date.parse(start))))
    )
      return fail(400, { message: 'Choose a valid date and time.' });
    try {
      if (kind === 'appointment' || kind === 'google')
        await apiRequest(
          kind === 'google' ? `/integrations/google/events/${id}/` : `/sales-appointments/${id}/`,
          {
            method: 'PATCH',
            body: {
              operation,
              starts_at: start,
              ends_at: end,
              title: String(form.get('title') ?? ''),
              internal_notes: String(form.get('internal_notes') ?? '')
            }
          },
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
    /** @type {Record<string, any>} */
    const body = Object.fromEntries(
      ['title', 'host', 'starts_at', 'ends_at', 'internal_notes', 'allow_overlap'].map((key) => [
        key,
        String(form.get(key) ?? '')
      ])
    );
    body.create_deal = form.get('create_deal') === 'on' ? 'true' : 'false';
    body.deal_name = String(form.get('deal_name') ?? '');
    body.deal_source = String(form.get('deal_source') ?? '');
    body.allow_overlap = form.get('allow_overlap') === 'true' ? 'true' : 'false';
    const selected = form.getAll('attendees');
    if (!selected.length && form.get('attendee')) selected.push(form.get('attendee'));
    body.contacts = [];
    body.companies = [];
    body.users = [];
    for (const value of selected) {
      const [kind, id] = String(value).split(':');
      if (!['contact', 'company', 'user'].includes(kind) || !/^[0-9a-f-]{36}$/i.test(id ?? ''))
        return fail(400, { message: 'Select a valid attendee.' });
      const key = kind === 'contact' ? 'contacts' : kind === 'company' ? 'companies' : 'users';
      if (!body[key].includes(id)) body[key].push(id);
    }
    try {
      await apiRequest('/sales-appointments/', { method: 'POST', body }, { cookies });
      return { created: true };
    } catch (err) {
      return fail(400, { message: readableError(err, 'Could not schedule event.') });
    }
  }
};
