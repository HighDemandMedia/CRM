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
activity and `gmail.send` for explicitly requested outgoing messages, and `calendar.events` / `calendar.calendarlist.readonly` for Calendar.
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
- Stores date, subject, sender, To/CC recipients, direction and full text. The message
  body is encrypted at rest. HTML is converted to text; remote images, tracking
  pixels and file attachments are not imported. Multipart text stored by Gmail
  as a body attachment is fetched to preserve complete message text.
- Contact and Company records have an **Emails** tab. Conversations are newest
  first, with search across subject, participants and message text, sent/received filters and 20 conversations per page.
  Open a conversation to read its messages oldest first, also paginated. Message
  text loads only when expanded; quoted history and recognizable signatures can
  be expanded separately. Open in Gmail continues in the connected mailbox.
- Company email history combines primary and explicitly linked contacts without
  duplicating a message addressed to several contacts. The contact filter narrows
  that history. Only contacts currently visible to the user are included.
- **Activity** keeps the latest 100 unique matching messages alongside record
  changes. Shared record Last Activity remains its property-change date.
- Only the connected mailbox owner can read these views, including administrators.
  Contact access is checked again when opening message text. Connected record views
  have no connect or refresh controls. Connection management and manual synchronization
  remain in Profile → Integrations.
- Adding a contact, changing its email or changing visible contacts restarts the
  bounded 90-day import on the next sync without clearing retained message history.
  Large mailboxes may require several jobs before older messages appear.
- Spam, trash and drafts are excluded; deletion detected in Gmail removes the
  cached message. Reading in the CRM does not mark messages read in Gmail.
- Sent/received activity is not proof of delivery, opening or reading by a recipient.

## Sending and internal comments

- **New email**, **Reply** and **Forward** use the current profile's connected Gmail,
  with the record's Edit permission enforced by the API. Plain-text messages support
  To and CC, up to 25 recipients. Attachments are not forwarded or composed here.
- Existing read-only Gmail grants continue importing mail. Reconnect once in
  Profile → Integrations to grant `gmail.send` before sending from the CRM.
- Replies preserve the original subject and Gmail thread headers. Newly synchronized
  mail honors Reply-To; older cached mail falls back to the sender until reimported.
  Forwarding creates a separate conversation and includes the quoted text in the draft.
- A durable request ID prevents duplicate sends. An uncertain provider response
  blocks automatic resending: check Gmail Sent before composing a new draft.
  Successful sends are cached immediately for matching, visible CRM contacts.
- **Internal comment** requires the record's Notes permission. It creates an internal
  record note with the email subject as reference, visible in Notes and Activity to
  teammates who can access that contact/company. It does not expose the mailbox or
  automatically copy the email body. Comments remain after Gmail is disconnected.
- Activity is the first/default tab and includes creation, actual field changes,
  assignments/associations, notes, attachments, appointments, and private sent/received
  email projections. Opening, downloading, and unchanged saves are excluded. Older
  unaudited changes cannot be reconstructed.

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
