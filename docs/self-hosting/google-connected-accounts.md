# Gmail and Google Calendar connected accounts

Each CRM profile authorizes its own Google account in Profile → Integrations.
Connections and cached data belong to that profile in that organization, including
when the same person belongs to multiple organizations. Organization administrators
cannot read another profile's mailbox or personal calendar through these endpoints.
The Gmail system sender is separate and its existing credentials remain unchanged.

## Google setup

1. In Google Cloud, enable **Gmail API** and **Google Calendar API**.
2. Configure the OAuth consent screen. For staging, add the email addresses of
   testers. For accounts outside your Workspace, use an external audience.
3. Create a **Web application** OAuth client dedicated to connected accounts.
4. Register the exact authorized redirect URI:
   `https://crm.highdemandmedia.com/profile/google/callback`.
   For local development use `http://localhost:5173/profile/google/callback`
   on a separate development client.
5. Configure these backend environment variables in the Render core group, shared
   by API, worker and scheduler:

   | Variable | Value |
   | --- | --- |
   | `GOOGLE_INTEGRATION_CLIENT_ID` | The new web client ID |
   | `GOOGLE_INTEGRATION_CLIENT_SECRET` | Its client secret |
   | `GOOGLE_INTEGRATION_ENCRYPTION_KEY` | One persistent Fernet key |

   Generate the encryption key privately using Python:
   `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`.
   Store it only as a secret. Keep it across redeploys and back it up securely;
   replacing it makes existing refresh tokens and cached email bodies unreadable.
   No client secret or encryption key belongs in the frontend service or Git.
6. Deploy API with the normal migration release step, followed by worker,
   scheduler and web. Keep exactly one scheduler.
7. In the CRM, Profile → Integrations → Connect Gmail / Connect Google Calendar.
   Select the desired calendar before creating CRM appointments. The primary
   Google calendar is used by default. A read-only calendar can be displayed but
   cannot receive changes from the CRM.

The OAuth flow requests identity and email plus `gmail.readonly` for mailbox
activity, and `calendar.events` / `calendar.calendarlist.readonly` for Calendar.
It uses PKCE, a short-lived single-use state bound to the current profile, an
HTTP-only browser state cookie, verified Google identity and encrypted offline
tokens. Users authorize Gmail and Calendar separately.

Google classifies `gmail.readonly` as restricted. External production apps need
Google's applicable verification and security assessment for server-side email
storage. A testing app is only for explicitly added testers; testing grants can
expire and require reconnecting. See [Google's scope documentation](https://developers.google.com/workspace/gmail/api/auth/scopes).

## Gmail behavior

- Imports the last 90 days in short resumable jobs, then polls Gmail history every
  five minutes. Expired history is rebuilt from the last 90 days.
- Records incoming and sent messages when the external address matches an active,
  visible CRM contact. No contacts are automatically created.
- Stores date, subject, sender, recipients, direction and full text. The message
  body is encrypted at rest. HTML is converted to text; remote images, tracking
  pixels and file attachments are not imported. Multipart text stored by Gmail
  as a body attachment is fetched to preserve complete message text.
- Activity appears on the contact, with an expandable message and link to Gmail.
  Only the connected mailbox owner can read it, and CRM contact permissions are
  checked again when the message is opened. The latest 100 matching messages are
  shown per contact. Shared record Last Activity remains its property-change date.
- Spam, trash and drafts are excluded; deletion detected in Gmail removes the
  cached message. This integration does not send emails or mark them read.
- Sent/received activity is not proof of delivery, opening or reading by a recipient.

## Calendar behavior

- Polls every five minutes. Calendar navigation reads the cache and does not wait
  for Google. Sync covers the previous 90 days and next 365 days, including timed,
  all-day and recurring instances. Google events are shown only to their owner.
- Exports the connected user's hosted CRM appointments, subject to Calendar
  permissions. Title, start, end and **meeting notes → Google description** sync
  in both directions. General contact notes are never exported. Connecting a host
  can publish the notes of existing hosted appointments in that window.
- Google changes to a linked appointment update the CRM appointment and attendee
  Appointment property through the same Calendar helper. Existing CRM appointments
  are not duplicated in the calendar cache display.
- Edit details, reschedule and cancel actions work on writable Google events.
  All-day Google events are opened in Google for editing.
- The CRM does not add invitees or send invitation/update emails as part of sync.
  Google notes may be visible to people who already have access to that event.
- Cached Google busy times are considered when creating or moving CRM appointments.
  Other hosts' availability exposes busy intervals, not their private event details.
- Stable external IDs and ETags make retries idempotent and detect concurrent edits.
  If both sides changed since the last sync, neither is overwritten. Align the
  conflicting event's title, dates and notes in Google with the desired CRM values
  (or cancel it on both sides) and sync again. The connection shows the conflict.
- Switching calendars with existing mirrors requires disconnecting first. Disconnect
  deletes CRM cached Google data and credentials, not the user's events in Google
  or their CRM appointments. Reconnecting to the same calendar reuses stable IDs.
  Switching to a different calendar leaves the previous Google events in place.

## Validation and activation

Automated tests use provider responses mocked locally. Actual OAuth consent,
Google API enablement, a real sent/received email and a real bidirectional calendar
round trip must be verified with the user's connected account after setup. No
production connection is implied by a successful local test.
