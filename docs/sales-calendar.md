# Sales Calendar

Calendar in Sell shows the appointment_at field of active contacts and companies accessible to the signed-in user. The list APIs enforce organization and record permissions before pagination. Only the visible date range is requested, with exclusive end timestamps and local browser timezone. All result pages are loaded. An appointment opens the source profile for editing. Company cards show the first associated contact when available and use that contact as a fallback for missing language, phone and email.

Legacy contact/company fields still support one appointment per record. The Create appointment button now creates independent SalesAppointment records with a stable UUID, organization, title, host Profile, UTC start/end, internal notes and creator metadata. Multiple independent appointments are supported. Users see appointments they host or created; org admins see all in their organization. Host selection is validated against active users in that organization. PostgreSQL RLS adds organization isolation. Day and week use a 24-hour grid with half-hour guides, scroll initially to 8 AM and place appointments at their local start minute. Overlapping cards use separate lanes. Cards reserve one hour of visual space for readability; this is not an appointment duration. Month remains unchanged; month shows six weeks. It does not invent duration or end time.

## Google Calendar integration

Personal Google Calendar and Gmail connections are now implemented. See [connected account setup and behavior](self-hosting/google-connected-accounts.md). Activation requires OAuth credentials and user consent.

The frontend consumes a normalized event shape: id, recordId, type, title, start, href and contact information. Source keys contact:<uuid> and company:<uuid> remain stable when the appointment time changes. The dedicated SalesAppointment model now exists with UUID and start/end. Future work should add associations and explicit source timezone and migrate the legacy single appointment fields without duplication.


New appointment cards open a details dialog with Host, start/end and internal notes. Day/week cards use their actual duration, with a minimum visual height for readability. The current creation form uses one local calendar date and requires end time after start time. Google sync runs in the background and exposes its status in Profile → Integrations.

Scheduling an event with an attendee updates that record's Appointment field in the same transaction and creates a Contact/Account Activity entry with the event title, server timestamp and acting user. Rescheduling updates the field if it still points to that event's previous start. Cancelling similarly clears it or chooses the earliest remaining future event. A newer or manually changed Appointment value is preserved. The calendar omits a legacy field card when a visible linked event represents the same attendee and timestamp, avoiding duplicate cards. Existing historical events are not backfilled by this change.
