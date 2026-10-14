# Privacy and legal release — draft, 2026-10-12

> Historical implementation/review record. The 2026-10-14 release supersedes
> the disabled-purge gates below: closure and automatic purge now default to
> enabled by the owner's decision. Read-only/export access lasts 30 days, then
> access is denied and the next daily scheduler cycle deletes active tenant
> data. Backup verification is not a prerequisite for this deletion. See
> [current release instructions](release-2026-10-14.md). Cloud backup/version
> retention and legal acceptance activation remain separate concerns.

## Status

Not effective or deployed. `CRM_LEGAL_VERSION` defaults to empty: invitation
acceptance is not yet enforced and no historical acceptance is invented.
Closure, reactivation and scheduled tenant purge are implemented locally.
`CRM_ORG_CLOSURE_ENABLED` defaults to true for owner-confirmed closure/cancellation.
`CRM_ORG_PURGE_ENABLED` remains false until irreversible-deletion release checks pass.
Do not advertise the proposed deletion period as operational yet.

Public identity: **High Demand Media**, **info@highdemandmedia.com**. No street
address or incorporation state is published. Initial market: United States.
Legal documents require review against actual operations before activation.

## Documents and controls

Website and CRM have separate privacy notices and terms, joined by a legal
center, in English and Spanish. The CRM presentation, login and profile show
only Privacy and Terms links. Provider details are part of the CRM Privacy Notice
(`#providers`), not a separate public page. The processing agreement (DPA) lives
in the CRM at `/legal/dpa`, accessible only after server validation of a pending
initial-administrator invitation or current organization administrator permissions.
It is linked before acceptance and from Organization settings for administrators.
The document source is server-only, and responses use `private, no-store`. Hosting is described accurately as Render and AWS; website
hosting uses Hostinger and quote notifications use FormSubmit.

CRM login/profile expose public legal links. New and existing invitees have an
unchecked terms acceptance when a version is active. Initial organization
administrators also confirm authority to accept on behalf of the organization.
Server validation applies to both invitation endpoints. Receipts contain user,
organization, version, language, authority and time, in the membership transaction.
The receipt is separate from a reusable invitation. This does **not** make current
users accept retroactively or introduce a terms-update acceptance flow.

Website quote forms have a separate unchecked promotional-email choice. The
choice and notice version are stored with the inquiry in the CRM submission and
internal email. It does not subscribe someone to a campaign or authorize SMS.
The website now uses a US-focused opt-out flow: Google/Meta tags start by default
unless a saved refusal, Global Privacy Control, or unavailable preference storage
blocks them. Footer privacy controls allow withdrawal. Previously sent
provider data cannot be erased by changing browser consent.

Before promotional campaigns, implement suppression/unsubscribe processing and
a valid postal contact address in those emails; the user's request not to publish
a street address on the website does not waive email requirements.

## Infrastructure observed (read-only, 2026-10-12)

- Rechecked after the owner's upgrade: Render `hdm-crm-staging-db` now uses the
  paid `0.1c-256mb` compute plan. Info no longer shows the Free expiry warning.
- Recovery advertises a 3-day PITR window, but initialization was still pending
  and Restore disabled at inspection. Create export is available; no export or
  restoration was performed. Actual recovery is not yet verified.
- S3 `hdm-crm-staging-queue`, us-east-1: versioning enabled, SSE-S3, Object Lock
  disabled, no lifecycle rules, no replication rules and no inventory configuration.
  The `media/` prefix was confirmed in the bucket.
- AWS Backup in the same account/region: zero protected resources, zero plans,
  Default vault with zero recovery points. Other accounts/regions are not certified.
- Owner clarified that the additional local CRM copy contains only dummy/demo data,
  not a production backup. No personal files were inspected or removed.
- The proposed 30-day noncurrent-version rule remains disabled and uninstalled.
  It applies to the shared `media/` prefix across tenants; activation can expire
  existing versions already older than 30 days. Review eligible versions first.

Detailed findings and activation gates:
[Backup and deletion review](backup-deletion-review-2026-10-12.md).

Sources: [Render backup documentation](https://render.com/docs/postgresql-backups),
[Render Free limitations](https://render.com/docs/free#free-postgres),
[S3 version deletion](https://docs.aws.amazon.com/AmazonS3/latest/userguide/DeletingObjectVersions.html).
Paid Render PITR depends on workspace plan (currently 3 days Hobby / 7 days Pro+);
logical exports are retained 7 days by Render. Verify the actual post-upgrade
panel rather than assuming a paid compute upgrade changes workspace plan.

## Closure and customer recovery implemented locally

The platform owner can initiate or cancel closure for any organization. Each organization owner can do so only for their own organization; other administrators and members cannot. The owner must confirm
with the organization name. Closure gives 30 days of read-only access under the
existing view/export permissions, blocks writes and public submissions, and stops
tenant background jobs. PostgreSQL locks wait for active jobs before closure.
Google credentials are cleared and pending invitations and notification deliveries
are canceled. Original Google messages and events are not deleted.

Before the deadline, the owner can reactivate the same organization without
restoring a backup. Records and memberships remain available. Users reconnect
Google; canceled invitations must be issued again. Reactivation does not resend
canceled form notifications. Recovery is allowed even if new closures are disabled.
After the deadline, the API refuses reactivation, even if a purge has not run yet.

The purge uses a separate disabled-by-default gate, tenant-scoped transactions,
a durable minimal deletion ledger, and the existing file-cleanup retry queue.
It covers attachments, comment files, organization/template logos and historical
documents. Shared users and storage keys still referenced elsewhere are preserved.
No laboratory modules were reintroduced. Unexpected protected relationships abort
and retain the organization for investigation; storage failures keep their receipts.

Before activation, complete the isolated cloud restore drill, external preservation
and replay of the deletion ledger, operational alerts for failures/overdue purges,
and inventory/approval of S3 noncurrent-version expiration. No per-tenant legal-hold
workflow is implemented: keep purge disabled if an exception requires retention.
See the [recovery runbook](organization-recovery.md).

## Release order (not authorized yet)

1. Complete cloud restore verification and the remaining operational gates. Obtain
   operational/legal approval of final EN/ES documents. Freeze an immutable copy
   of each version and have acceptance links resolve to that version.
2. Publish the approved website documents and check all public URLs. Current
   local pages say **Draft / not effective** and are `noindex`. The public bundle
   no longer contains `crm-dpa.html`, `crm-dpa-es.html`, `crm-providers.html` or
   `crm-providers-es.html`. If an older bundle was uploaded, remove those four
   files on the host too: extracting a new ZIP does not remove stale files.
3. Deploy API with `0078_legal_acceptance` and `0079_organization_lifecycle`;
   run normal release migrations. Deploy Web, Worker and Scheduler with the same code. Keep `CRM_LEGAL_VERSION` empty while documents/flows remain drafts.
4. Set a reviewed document version only after the public notices and administrator-only DPA
   are available and invitation previews/forms have been verified. Existing users are not
   automatically covered by new invitation acceptance.
5. Closure workers/scheduler deployment and activation are a separate gate once
   the remaining recovery and operational gates pass. Do not enable storage expiration merely
   because this migration has been deployed.

The website working copy is outside this Git repository at
`../work/website-crm-hostinger-v2`; its authoring/verification files and a baseline
copy are in `../work/legal-2026-10-12`. Current changes are local only.

## Verification of this draft

- 64 backend invitation/auth tests passed, including rejection of missing/stale
  consent, initial-admin authority, wrong invitee and rollback on receipt failure.
- 36 frontend invitation/legal/settings tests passed, including private DPA access
  for administrators and rejection of anonymous visitors, ordinary team invitations,
  expired/revoked invitations and failed permission checks.
- 8 website tracking-choice tests passed during the initial implementation.
- Anonymous local HTTP request to `/legal/dpa` returns 403 with `no-store` and
  no document content. EN/ES agreement text is absent from the public client
  JavaScript build. Targeted lint has no errors; six existing unkeyed-loop
  warnings remain in Organization settings.
- 14 website pages checked for local links, draft notices and optional unchecked
  quote-form consent. No real email or public-form submission was sent.
- Svelte check: 0 errors and warnings. Production frontend build passed.
- Full frontend formatting and lint passed with existing lint warnings; targeted
  new legal components/utilities passed lint without warnings after cleanup.
- Backend migration dry-run has no outstanding model changes; targeted Ruff passed.
- Simplified legal center EN/ES and private Spanish DPA checked in the local
  browser with the existing local administrator session, including the DPA link
  in Organization settings. No agreement was accepted during verification.
  At the available 877px viewport there was no horizontal overflow. Mobile sizing
  could not be confirmed because the browser viewport override did not apply.
- Reviewed the invitation changes and `git diff --check` passed. Pre-existing
  Tasks/Tickets changes were preserved and not included in this test claim.
- Nothing committed, pushed, published or deployed. No live database migration,
  service plan change, lifecycle rule application or deletion was performed.
