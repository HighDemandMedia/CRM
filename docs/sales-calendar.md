# Sales Calendar

Reviewed against the implementation on 2026-11-01.

Calendar combines permitted CRM appointments, legacy contact/company appointment fields,
and the signed-in user's connected calendar data. Organization and record permissions apply;
connection ownership does not grant access to another user's private calendar or mailbox.

Schedule event creates a SalesAppointment with a generated record ID, host, start/end,
attendees, associations and private internal notes. Multiple events per record are supported.
The host must be an active user in the organization. Day/week cards use the event duration
with a minimum display height; overlapping appointments occupy separate lanes. The display
height is not a second appointment duration. Dates and times use the applicable calendar zone.

## Google Calendar

The connected calendar receives CRM appointments. Profile → Integrations loads availability
calendars automatically in a searchable multiple-selection dropdown. Selected calendars appear
as removable labels. Additional calendars contribute busy intervals, not duplicate CRM events.
Only authorized calendars can be selected; a read-only calendar is not a writable destination.

Guest invitations support acceptance, tentative responses and declines. The CRM shows response
status and updates the linked invitation when rescheduling or cancelling. Internal CRM notes
are excluded from Google's event description and from guest invitations. Google-originated
descriptions are separate from CRM private notes. Push notifications trigger background
synchronization; foreground refresh and periodic recovery handle delayed or missed notices.
This is near-real-time synchronization, not an instantaneous-delivery guarantee.

See [connected accounts](self-hosting/google-connected-accounts.md) and
[Calendar push](operations/calendar-push-sync.md) for configuration and operational details.

## Legacy appointment fields

Scheduling with an attendee updates that record's Appointment field in the same transaction
and creates an activity with the event title, timestamp and acting user. Rescheduling updates
that field only if it still points to the previous event start. Cancellation clears it or
chooses a remaining future event. A newer or manually changed Appointment value is preserved.
The calendar omits a legacy field card when a visible linked event represents the same attendee
and timestamp. Historical legacy data is not automatically backfilled into new appointments.
