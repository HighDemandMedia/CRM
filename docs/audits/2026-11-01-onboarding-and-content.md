# Onboarding and product-content audit — 2026-11-01

## Scope and release boundary

Local implementation and documentation review. No commit, push, deployment, Google
verification submission or public-policy publication was performed in this change.
Production approval/status and live cloud configuration were not re-audited.

## Implementation

- Profile setup reuses AppearanceSettings and NotificationPreferences. Light/Dark is
  immediate and browser-local. Notification topics/channels autosave to the authenticated
  user/organization through the existing self-profile action and API.
- Onboarding presents separate profile, appearance, notification and review screens;
  initial administrators also complete organization setup. Back/Continue preserves form
  drafts and notification selections. No browser permission request occurs on page load;
  enabling Browser retains the existing explicit user-gesture permission flow.
- Continue is blocked while a notification save is pending; preferences cannot change
  during profile submission. Existing errors/rollback, permission and setup-step gates remain.
- No schema, role, integration scope, session policy or notification defaults changed.

## Knowledge review

Added guides for notification channels, appearance and CSV import/export. Corrected
existing guides covering contact/company identity and duplicates, inline editing,
object creation/actions, task reminders, guest invitations, calendar availability,
Gmail push/fallback behavior, report date selection, required creation fields,
onboarding and fixed session expiry. Updated the corresponding getting-started,
preferences, calendar, help and connected-account documentation. Historical release
and Console records remain dated and are explicitly distinguished from current guidance.

## Policies reviewed

| Material | Result |
| --- | --- |
| Public CRM privacy EN/ES | Prepared corrected pages in `docs/legal/public`; publication still pending. |
| Public CRM terms EN/ES vs server-only terms JSON | Every section text matches the public snapshot retrieved for this audit. No contractual change required for these preferences. |
| DPA EN/ES | Existing communication, calendar, provider, security and closure clauses remain consistent with the reviewed implementation; version and acceptance records unchanged. |
| Google disclosures / guides | Separate connections, private notes, user-scoped mailbox access and best-effort synchronization documented. Historical combined-client submission wording is marked superseded. |

The published privacy text incorrectly described CRM meeting notes as synchronized to
Google and visible to guests. `backend/common/google_sync.py` sends an empty Google
event description for CRM appointments; internal notes remain private. The prepared
notice corrects this and explains selected-calendar busy checks, attendee responses,
Gmail Pub/Sub metadata, notification preferences, browser permission/previews, local
appearance/list choices, duplicate-alert receipts and fixed session deadlines.

The provider/retention/security clauses were reviewed for consistency with the existing
implementation, not certified as legal compliance or provider contract fulfillment.
No new claims of accessibility certification, instant delivery, Google approval or
security-assessment completion were added. The Google disclosure reference is the
[Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy).

## Verification

- Frontend: 140 test files / 1,131 tests passed; includes onboarding access/step gates,
  personal notification-settings passthrough, notification delivery and legal access tests.
- Backend: 57 onboarding, notification-channel/API and legal-acceptance tests passed
  (8 warnings). The container lacks the repository coverage configuration, so these
  targeted tests ran with coverage addopts disabled.
- Svelte check: zero errors and zero warnings. Full Prettier and ESLint passed.
- Production frontend build passed. Final diff whitespace check passed.
- Local browser: Light/Dark rendering; separate wizard screens; Back/Continue and final review; Bell toggle autosave;
  reload retained the saved choice; original choice restored; Open CRM completed setup.
  Local profile setup, notification preference JSON and time zone restored exactly afterward.
- No external email, real browser-permission grant or Google authorization was needed.
  Those delivery integrations were not retested by this content/onboarding change.
- Public terms parity checked in English and Spanish. Privacy publication assets retain
  existing website navigation/styles and provider links; the public website is unchanged.

## Follow-up

Publish the two prepared privacy files with the next approved release and verify both
language URLs. Knowledge article bodies remain English as before; new controls use the
existing English/Spanish UI translations. This is a functional/content consistency audit,
not a jurisdiction-wide legal opinion or a complete accessibility audit.
