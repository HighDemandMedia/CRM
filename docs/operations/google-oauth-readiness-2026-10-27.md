# Google OAuth verification readiness — 2026-10-27

Pre-release implementation and review record. Deployment must be verified separately;
this document does not establish Google submission, approval or certification.
No production credentials, sessions, Google grants or records changed during this work.
This supersedes the submission checklist in the historical October 14 notes, not
Google's own decision or the required external security assessment.

## Implemented locally

- Gmail and Calendar each show a concise EN/ES data-use disclosure before redirecting
  to Google. Both the Web action and API require an explicit affirmative continuation.
  The compact dialog shows one feature row and a privacy summary; detailed retention
  and revocation information remains in the linked policy. There are no decorative
  selection checkboxes for features users cannot toggle.
  Sign-in stays separate: Google provides identity, never the Google password.
- Disconnect still removes only the chosen service from the current CRM profile.
  Remove Google access is a separate, confirmed action: Google's revocation may
  also invalidate other HDM grants for the same Google account/project. It can
  therefore affect another organization or an HDM system sender using that account.
  Cleanup here is limited to matching connections in the current user's organization;
  other profiles detect rejected grants on their next refresh. This is not an
  organization-wide or platform-wide admin revocation tool.
- Revocation sends the token in the HTTPS request body to Google's revocation endpoint.
  Provider failures preserve the local credential for a retry and expose no raw response.
  An already invalid token is handled idempotently; another stored service token is
  tried before declaring cleanup complete. Replaced connection generations are preserved.
- A confirmed `invalid_grant` refresh rejection clears encrypted credentials and the
  connection's private message/event cache, and requires reconnecting. Transient errors,
  invalid client configuration and generic API 401/403 errors do not trigger this deletion.
  CRM appointments, independent records and internal comments remain unchanged.
- Gmail does not enumerate a mailbox when there are no accessible contact email addresses.
  Existing matching, paging, permissions, send/reply/forward and calendar behavior remain.
- In-app help explains disconnection and retention. Public privacy links use the same
  clean EN/ES URLs supplied to Google.

## Scope inventory to reconcile in Google Cloud

Do not request a broader scope to simplify verification. The runtime scope sets did
not change in this patch. Console declarations must include the union used by all
clients in the project; non-sensitive identity scopes still need accurate declarations.

| Scope | Actual purpose | Client / minimum justification |
| --- | --- | --- |
| `openid` | Verify Google account identity | Sign-in, connected accounts and system sender |
| `https://www.googleapis.com/auth/userinfo.email` | Verified email and account matching | Same clients; no contact discovery |
| `https://www.googleapis.com/auth/userinfo.profile` | Name for sign-in and onboarding | Sign-in only; code uses Google's `profile` alias |
| `https://www.googleapis.com/auth/gmail.readonly` | Read messages matched to accessible CRM contacts | Connected accounts. Headers are inspected for matching, then matched text and metadata are cached. No message modification/deletion. `gmail.metadata` cannot supply message text. |
| `https://www.googleapis.com/auth/gmail.send` | User-requested compose/reply/forward and transactional system mail | Connected accounts and separate system sender. Read-only scope cannot send. |
| `https://www.googleapis.com/auth/calendar.calendarlist.readonly` | List calendars and let users select one | Connected accounts. Calendar lists are not modified. |
| `https://www.googleapis.com/auth/calendar.events` | Read selected calendar events and synchronize/create/update/cancel linked CRM appointments | Connected accounts. Read-only cannot write; app-created-only scopes cannot read users' existing events needed for their calendar/availability. |

At the latest read-only Console review, `openid` and profile were absent from Data
Access, and the Gmail justification described only replies to CRM-sent messages.
Replace that justification: the app also imports other sent/received messages matched
to accessible CRM contacts. Do not claim it reads only replies.

Suggested Gmail justification:

> HDM CRM lets a user view sent and received email history for their accessible CRM
> contacts. The initial import checks headers within the last 90 days to match contact
> addresses, then reads and stores matching message metadata and encrypted text.
> Ongoing background synchronization updates that history. Only the connected user can
> read their mailbox in the CRM. Users can compose, reply and forward with gmail.send;
> the separate system sender uses gmail.send for invitations and transactional notices.
> We do not modify mailbox messages, import attachment files, use Google data for ads,
> sell it, send it to AI services, or provide cold-email or email-warming features.
> Metadata-only access cannot provide the message text required by this feature.

The initial 90-day import is **not** a 90-day storage expiration. Relevant cached mail
can remain while connected. Disconnection clears the selected connection's active
cache; expired/revoked grants clear it when detected. Matching messages are also
removed when Gmail deletion or loss of visible contact association is detected.
Separate CRM comments/records and residual infrastructure backups have their own
retention; do not promise that disconnecting instantly erases every backup copy.

## Local website copy

Updated only the active local candidate's `crm-privacy.html` and
`crm-privacy-es.html` under `../work/service-expansion-20261026/website-candidate`
(relative to the repository root). No forms, tracking, styling or other pages
were changed. The changes explain header matching, background sync, retention,
revocation and no transfer of Google data to third-party AI/ML services.
Provider wording no longer assigns quote notifications to FormSubmit or mail delivery
to AWS: quotes use the CRM and its Google system sender; AWS stores files and Render
hosts/processes the CRM. The provider inventory must be rechecked if deployment changes.
The website working copy is outside this repository and needs its own approved
publication. Do not deploy the unrelated service-expansion redesign merely to publish
these privacy corrections; publish the two reviewed legal pages against the current site.

## Still required outside this patch

1. Review and publish the two public privacy pages with the functional release.
2. Update Data Access declarations/justifications in Google Cloud; preserve current
   credentials, clients and redirects. Separate production and development projects
   as a planned operational change, not an untested credential replacement here.
3. User records the demo: invitation/sign-in; Profile → Integrations; new disclosure;
   Google consent showing app identity and scopes; Gmail matching, read, send, reply;
   calendar selection, create/update/cancel and two-way sync; disconnect/privacy links.
   Use fictional records and an authorized test mailbox. Cover the system sender's
   transactional use as well. Never show passwords, tokens or secrets.
4. Provide a working invited CRM reviewer account at
   `https://crm.highdemandmedia.com/login`. These are CRM credentials, not Google
   credentials. Confirm the reviewer can reach Integrations without onboarding or
   account-access blockers. Do not disable security or provide a development bypass.
5. Complete CASA/security assessment if Google requires it for server-side restricted
   Gmail data. Unit tests and this checklist do not establish certification. Verify
   the required tier/process with Google; do not invent a certificate or exemption.
6. Reply to the verification email only after the above evidence is ready. No reply
   or submission is authorized by this local implementation request.

## Release procedure and validation

No database migration, dependency change or OAuth scope expansion is needed.
Web sends the new disclosure field, accepted harmlessly by the previous API; deploy
Web before the new API. Then deploy API, Worker and Scheduler from the same revision.
Old open browser tabs must reload before starting a connection against the new API.
Keep one Scheduler. Confirm CI before deployment and validate real OAuth with the
owner's test account after release. Real revocation can affect other connections:
use a dedicated test Google account and explicit approval for that destructive check.

Sources:
- https://developers.google.com/identity/protocols/oauth2/policies
- https://developers.google.com/identity/protocols/oauth2/web-server#tokenrevoke
- https://developers.google.com/workspace/gmail/api/auth/scopes
- https://developers.google.com/workspace/workspace-api-user-data-developer-policy
- https://support.google.com/cloud/answer/13465431

## Verification completed locally

- 93 backend tests passed: Google integration, privacy controls, record-mail reading,
  sending/actions and Google invitation flows. Google responses were mocked; no real
  OAuth grant was revoked and no real message was sent.
- 1,080 frontend tests passed across 133 files, including disclosure rejection,
  affirmative continuation, secure state cookie/redirect and revocation forwarding.
- Svelte check: 0 errors / 0 warnings. Full frontend ESLint, Prettier and production
  build passed. Targeted backend Ruff and `git diff --check` passed.
- Actual Profile → Integrations loads with the local session. Local Google is not
  configured, so connection buttons correctly remain disabled. An isolated temporary
  local component preview exercised EN/ES dialogs, Cancel/Escape/focus and layouts at
  desktop 1280, tablet 768 and mobile 320 pixels. At 320px, the body scrolls within the
  dialog while the actions remain visible. That preview route was removed before the
  final checks/build; no testing bypass or fixture route remains in the application.
- Both local privacy pages were checked against their backups: only the Google and
  provider sections and revision date changed; navigation, forms, scripts and styling
  remain identical. Backups and visual evidence are in
  `../work/google-oauth-review-20261027` relative to this repository.
- Eight existing Django 7 mail-setting deprecation warnings remain in backend tests.
  They are not test failures or introduced by this patch; mailer migration is separate.

Real Google consent, token revocation and a live email/calendar round trip remain
post-release checks with a dedicated authorized test account. No production, Google
Cloud, Hostinger or Git publication occurred during this local preparation.

## Follow-up: compact disclosure and privacy accuracy

Reviewed the supplied Google verification email and the official Workspace data policy
(https://developers.google.com/workspace/workspace-api-user-data-developer-policy).
Both EN/ES privacy copies explicitly describe data types, user-requested outgoing
messages/attachments, HTTPS, provider processing, permitted transfers and limits on
human access. The short dialog still discloses collection/storage, background sync,
use, hosting-provider processing and relevant visibility before affirmative consent.
No new permissions, API behavior or publication in this follow-up.

Retention remains tied to actual connection and infrastructure lifecycles; do not
promise immediate destruction of all backups or a fixed backup deadline that has not
been verified. This review does not certify Google approval or CASA completion.
