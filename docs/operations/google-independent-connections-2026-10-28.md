# Independent Google connections

This code does not create Google Cloud projects, submit verification, revoke live
grants or migrate users automatically. Deployment and user authorization are separate steps.

## Configuration contract

Google revokes grants at **project**, not individual scope or client, level.
Use separate Cloud projects for Gmail and Calendar, both different from sign-in,
the original shared integration project and the system email sender. Existing
sign-in (`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`) and system-mail credentials
remain unchanged during the first phase.

| Purpose | Backend variables |
| --- | --- |
| Sign-in | Existing `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`; add `GOOGLE_PROJECT_ID` |
| Legacy system email sender | If retained for rollback, existing `GMAIL_SYSTEM_*` credentials require `GMAIL_SYSTEM_PROJECT_ID` |
| Existing shared connections | Keep `GOOGLE_INTEGRATION_CLIENT_ID`, `GOOGLE_INTEGRATION_CLIENT_SECRET`; add `GOOGLE_INTEGRATION_PROJECT_ID` |
| Independent Gmail | `GOOGLE_GMAIL_CLIENT_ID`, `GOOGLE_GMAIL_CLIENT_SECRET`, `GOOGLE_GMAIL_PROJECT_ID` |
| Independent Calendar | `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET`, `GOOGLE_CALENDAR_PROJECT_ID` |
| Encryption | Keep `GOOGLE_INTEGRATION_ENCRYPTION_KEY` unchanged |

Project IDs must be copied from the **actual project owning each OAuth client** in
Cloud Console. The CRM checks these declared IDs and rejects collisions, missing
metadata and duplicate client IDs; it cannot discover project ownership from Google
using a refresh token. Console verification of this mapping is an activation gate.
Do not invent different IDs to bypass the check. Secrets remain backend-only.

If a dedicated client's configuration is entirely absent, new connections still
use the original shared client. A partially populated dedicated configuration
blocks new authorization for that service instead of silently using the wrong client.
Existing tokens continue refreshing with their issuing client during migration.

## Google Cloud preparation

1. Keep the current project and clients intact. Inventory login, shared integrations
   and system sender before changing anything.
2. Create separate development and production projects as required by Google's
   environment separation policy. Each dedicated Gmail project enables Gmail API;
   each Calendar project enables Google Calendar API.
3. Configure branding, support email, authorized domains, homepage and privacy
   policy for each public application. Use identifiable Gmail/Calendar app names.
4. Create a Web application client in each integration project. Authorized redirect:
   `https://crm.highdemandmedia.com/profile/google/callback` in production.
   In development use the exact configured `FRONTEND_URL` plus
   `/profile/google/callback` (for example `http://127.0.0.1:5181/profile/google/callback`).
   `localhost` and `127.0.0.1` are different redirect origins.
5. Gmail requests `openid`, `userinfo.email`, `gmail.readonly`, `gmail.send`.
   Calendar requests `openid`, `userinfo.email`, `calendar.events`,
   `calendar.calendarlist.readonly`. This change adds no scopes.
6. Each project's applicable branding/data-access verification is independent.
   Gmail restricted-scope/security-assessment obligations remain. Start with
   authorized test users; do not describe this preparation as approval by Google.

## Rollout and data handling

1. Run the local regression suite and additive `common.0086` migration. Existing
   connection rows receive blank provenance, meaning the original shared client.
   Database defaults also accommodate older instances during a rolling release.
2. Deploy the compatible API, Worker and Scheduler code with the usual migration
   release command, followed by Web. Keep one Scheduler. Do not activate new
   credentials while any backend process still assumes the shared client.
3. Add the verified project metadata and dedicated credentials to API, Worker and
   Scheduler together. Keep shared credentials and the encryption key.
   `check_hosted_config` rejects conflicting dedicated projects at release time.
4. A connected legacy service displays **Reconnect** once a valid dedicated client
   is available. The user must authorize the new application. Pending authorization
   records its client separately; cancellation, missing scopes or failed consent
   leave the active connection/cache intact. Only a successful callback switches
   the token and resets the private sync cache for reimport. CRM records remain.
5. An independent service's **Disconnect** calls Google's revoke endpoint before
   removing its local credentials/cache. Timeout or an unexpected provider rejection
   preserves them and shows an error. If the token is already unusable or absent,
   local cleanup is allowed without claiming Google confirmed grant revocation.
   Cleanup removes only this profile's selected service; original Google
   messages/events and CRM records remain.
6. Legacy **Disconnect** continues local-only cleanup. **Advanced options → Revoke
   shared Google access** remains only for legacy connections, with confirmation.
   It cleans only connections belonging to that same Google project/account in
   this profile, not already migrated connections in other projects.
7. Google project-wide revocation can still affect the **same service/account in
   another organization**. Separate projects isolate services, not CRM tenants.
   Other profiles clear unusable cached data when their refresh rejection is detected.
8. The system does not silently revoke the old shared project after migration: it
   can still serve sign-in or the system sender. Retire it only after separately
   auditing all of those dependencies and obtaining authorization.

Do not remove/replace credentials while rows still reference their client. A missing
issuer configuration produces an actionable error and preserves data. Secret
rotation for the same client is supported. Once independent grants exist, rollback
must retain code capable of routing them; do not roll back to shared-client-only code.

## Local verification — 2026-10-28

- 129 backend tests passed across integration, privacy, hosted configuration,
  invitation, system sender and record mail actions (mocked Google responses).
- The 28 separation tests also passed with migrations enabled on a fresh test database.
- Migration 0086 was applied to local PostgreSQL without replacing existing connections;
  column defaults were verified against the final migration. No pending model changes.
- 14 frontend action tests passed; ESLint and Ruff passed. Svelte check reported
  zero errors and zero warnings; the production frontend build completed.
- After the user authorized both development applications, local Integrations showed
  Gmail and Calendar connected with individual Disconnect actions and no Advanced
  options section. Both saved connections match their respective configured OAuth
  client/project, with distinct client IDs and declared project IDs. Project metadata
  is configuration evidence, not independent verification of Cloud project ownership.
- Real token refresh and read-only provider requests passed for both connections:
  Gmail's profile matched the connected account and Calendar's calendar-list request
  succeeded. Both connections had completed synchronization with no stored errors.
  Checks used the organization's RLS context and did not print credentials or mail
  contents. No mail was sent, events created, or Google permissions revoked during
  this initial verification.
- The user subsequently authorized a real local Gmail disconnect. The UI reported
  confirmed Google permission removal and Gmail's connection row was removed.
  Calendar remained connected: a fresh token refresh and calendar-list API request
  succeeded after Gmail revocation. Gmail is left disconnected for user reconnection.
  The reverse Calendar-disconnect test, CRM Google sign-in and system sender checks
  have not been performed with these development projects.
- Fixed stale callback feedback during connection management: newer results suppress
  the old callback notice, and management actions remove its query parameter so it
  does not reappear on reload.
- Existing Django mail-setting deprecation warnings remain (nine in this test run);
  migrating those settings to Django's MAILERS configuration is outside this change.
- No commit, push, cloud configuration change or production deployment was performed.

## Final activation checks

System-generated production mail now uses Amazon SES. The legacy Google sender
credentials are retained for rollback only; this OAuth rollout does not change
`EMAIL_BACKEND`, SES credentials, or the sign-in client.

Production preparation on October 28 confirmed the dedicated Gmail and Calendar
client IDs in Render match their respective Cloud projects, with the callback
`https://crm.highdemandmedia.com/profile/google/callback`. Both apps are still in
Testing, with the two owner-controlled test accounts. Their required scopes were
added to Data Access; this is not Google verification approval. A fresh local run
passed 123 integration, privacy, invitation, hosted-config and mail tests. Existing
mail API deprecation warnings remain. The legacy integration tests now explicitly
clear dedicated-client configuration so developer environment values cannot alter
their intended shared-client scenario.

- Development consent and callbacks passed; repeat with the production projects.
- Gmail: import, send/reply/forward with an approved test mailbox; disconnect Gmail
  and confirm Calendar sync and CRM sign-in still work.
- Calendar: create/update/cancel a controlled appointment; disconnect Calendar and
  confirm Gmail and sign-in still work. Verify system email separately.
- Test a legacy and migrated connection together, including failed/cancelled consent.
- Reconcile public privacy wording and the verification videos with the actual
  migration state before public release. In-app help already describes both modes.
- A local mocked test does not prove provider consent, delivery, revocation or
  Google approval. These real checks require the newly configured projects.

References:

- [Google token revocation](https://developers.google.com/identity/protocols/oauth2/web-server#tokenrevoke)
- [OAuth policies](https://developers.google.com/identity/protocols/oauth2/policies)
- [Separate-project verification](https://developers.googleblog.com/en/get-smart-about-preparing-your-app-for-oauth-verification/)
