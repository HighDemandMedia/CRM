import { apiRequest } from '$lib/api-helpers.js';
import { json, error } from '@sveltejs/kit';
import { listContacts } from '$lib/server/v2/contacts.js';
import { listAccounts } from '$lib/server/v2/accounts.js';

/** @type {import('./$types').RequestHandler} */
export async function GET({ cookies, url }) {
  const start = url.searchParams.get('start'),
    end = url.searchParams.get('end');
  const from = Date.parse(start ?? ''),
    to = Date.parse(end ?? '');
  if (!Number.isFinite(from) || !Number.isFinite(to) || to <= from || to - from > 43 * 86400000)
    error(400, 'Invalid calendar range.');
  async function collect(loader, type) {
    const events = [];
    let offset = 0;
    while (true) {
      const params = new URLSearchParams({
        calendar_start: new Date(from).toISOString(),
        calendar_end: new Date(to).toISOString(),
        limit: '100',
        offset: String(offset),
        is_active: 'true',
        sort: 'name'
      });
      const page = await loader({ cookies }, params);
      for (const record of page.results) {
        if (!record.appointment_at) continue;
        const contact = type === 'company' ? record.contacts?.[0] : null;
        const contactName = contact
          ? [contact.first_name, contact.last_name].filter(Boolean).join(' ')
          : '';
        events.push({
          id: `${type}:${record.id}`,
          recordId: record.id,
          type,
          title: record.name,
          start: record.appointment_at,
          contactName,
          language: record.language || contact?.language || '',
          phone: record.phone || contact?.phone || '',
          email: record.email || contact?.email || '',
          href: `/${type === 'contact' ? 'contacts' : 'accounts'}/${record.id}`
        });
      }
      offset += page.results.length;
      if (offset >= page.totals.count || !page.results.length) break;
    }
    return events;
  }
  const [contacts, companies, appointments] = await Promise.all([
    collect(listContacts, 'contact'),
    collect(listAccounts, 'company'),
    apiRequest(
      `/sales-appointments/?${new URLSearchParams({ start: new Date(from).toISOString(), end: new Date(to).toISOString() })}`,
      {},
      { cookies }
    )
  ]);
  // A linked event is also reflected in the attendee's Appointment field.
  const linked = new Set(
    appointments.flatMap((a) => [
      a.contact ? `contact:${a.contact}:${Date.parse(a.starts_at)}` : '',
      a.company ? `company:${a.company}:${Date.parse(a.starts_at)}` : ''
    ])
  );
  const legacy = [...contacts, ...companies].filter(
    (event) => !linked.has(`${event.id}:${Date.parse(event.start)}`)
  );
  return json(
    {
      events: [
        ...legacy,
        ...appointments.map((a) => ({
          id: `appointment:${a.id}`,
          type: 'appointment',
          title: a.title,
          start: a.starts_at,
          end: a.ends_at,
          host: a.host_name,
          hostId: a.host,
          notes: a.internal_notes,
          attendee: a.attendee,
          contactName: a.attendee?.name ?? '',
          language: a.attendee?.language ?? '',
          phone: a.attendee?.phone ?? '',
          email: a.attendee?.email ?? '',
          href: '#'
        }))
      ].sort((a, b) => Date.parse(a.start) - Date.parse(b.start))
    },
    { headers: { 'Cache-Control': 'private, no-store' } }
  );
}
