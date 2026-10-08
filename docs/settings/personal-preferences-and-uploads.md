# Personal preferences and attachment limits

## CRM language

In **Profile → Profile info → Regional preferences → CRM language**, choose English or
Español and save. This is a personal account preference, shared across the user's
organizations and devices after the next page load. It does not change another user's UI,
organization terminology, record contents, communication language, or email templates.

`User.ui_language` is authoritative (`en` or `es`, English by default). The existing
`/org/ui-context/` response supplies it to the frontend. A non-sensitive, HTTP-only
`crm_language` cookie also remembers the language on sign-in pages in the same browser.
The translation context belongs to each Svelte layout/request; there is no mutable global
locale shared between users. The Spanish catalog lives in `frontend/src/lib/i18n/es.json`.
Unknown messages fall back to their original English text. Customer-authored text is not
automatically translated; help article bodies and external service errors may remain English.

Deploy database migration `common.0072_user_ui_language` before the updated web application.
The existing communication **Language** field remains separate.

## List preferences

Contacts, Companies, Deals, Tasks and Tickets remember visible columns and their order.
Contacts, Companies and Deals also remember their resizable column widths. Returning to a
module from navigation opens its list view, even if pipeline mode was previously selected.
Pipeline mode is a temporary choice in the current URL; refreshing or opening an explicit
pipeline link preserves that choice. Old saved view modes are ignored. Sort direction/field
are still restored when opening a bare module URL. Explicit URL parameters take precedence.
Search terms, filters and pagination are not saved.

These presentation preferences use browser local storage, scoped by organization, signed-in
user and object. They survive module navigation, reloads and closing/reopening a browser tab.
Column selection/order and widths also update in other open tabs. Sorting restores on
reopening a module, rather than redirecting another tab while it is in use.

Preferences do not transfer to another browser/device. Clearing browser site data removes
them; private browsing or blocked storage can prevent persistence. A corrupt or unavailable
store falls back to the default view without blocking the CRM. Former unscoped column widths
are intentionally not migrated because they cannot be attributed safely to a user/organization.

## Attachments

CRM record attachments have a **25 MiB per-file limit** (26,214,400 bytes, shown as “25 MB” in
the interface). The API already enforces this limit before saving a row or uploading to S3.
The shared attachment picker, ticket composer, and frontend API forwarding layer reject
oversized files too, with a useful message. Files exactly at the limit are accepted.
Profile photos and support uploads retain their existing, separate limits.

`frontend/Dockerfile` sets the Node adapter `BODY_SIZE_LIMIT` to 27,262,976 bytes (26 MiB),
allowing a single 25 MiB file plus multipart overhead. A Render environment variable with the
same name overrides that default: check the **Web** service for an old smaller value before
deployment. Keep any upstream proxy limit consistent. This is an upload limit, not a promise
that an attachment of that size can be delivered by every email provider.

This change does not introduce a total organization storage allowance or change S3 permissions.
S3 is elastic storage, not a fixed-capacity disk with a remaining-space figure. Monitor stored
bytes/object count and cost separately. Bucket Metrics/Storage Lens statistics may be delayed;
use **Objects → select prefixes → Actions → Calculate total size** for a current object listing
when available.

References: [Amazon S3 FAQ](https://aws.amazon.com/s3/faqs/),
[S3 daily storage metrics](https://docs.aws.amazon.com/AmazonS3/latest/userguide/metrics-dimensions.html),
[Gmail attachment limits](https://support.google.com/mail/answer/6584?hl=en).

## Invitation setup

Accepting a new invitation starts persistent setup on that organization membership.
Both new accounts and existing users joining another organization confirm their full
name, CRM language and personal time zone in Profile before opening CRM modules.
Phone and communication language remain optional; a blank personal time zone inherits
the organization default. Existing memberships are not retroactively enrolled.

The initial administrator invited by the platform owner then completes Organization
information and confirms its name, currency and time zone. Ordinary team invitations
never grant access to organization setup or change roles. Closing the browser does not
clear pending setup: the app resumes the membership's saved step after sign-in.

`common.0073_profile_setup_step` adds the state with a completed default for existing
memberships. Completion is validated by the existing self-profile and organization
settings APIs; the frontend shell reads it from its existing UI-context request.
Deploy the API and apply migrations before the matching Web release.

## Session review (2026-10-07)

The API currently issues one-hour access tokens and fourteen-day refresh tokens.
Refreshing rotates the refresh token and starts a new fourteen-day validity window;
there is no separate absolute session deadline or inactivity timer. Auth cookies
are persistent, so closing a normal browser tab/window is not an explicit logout.
Sign out clears the cookies and attempts to revoke the refresh token at the API.

The web session now refreshes whether the access cookie is expired or already absent.
Password, Google, magic-link sign-in, and organization switching share the same cookie
writer (one hour for access; fourteen days for refresh and organization). Successful
renewal replaces the rotated token and renews the selected organization's cookie.
If the organization cookie is missing, it is restored from the API-issued access token.
Invalid or revoked renewal clears authentication cookies and requires sign-in. Closing
an incognito session or clearing site cookies still removes the browser session.
