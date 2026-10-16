# Render and AWS readiness review — 2026-10-16

## Outcome

Live infrastructure checks passed and the approved configuration changes below
were saved. This is not a certification of every customer workflow. No deployment,
purchase, database export, restore, or organization deletion was initiated.
Existing local application changes were preserved.

## Applied changes

| Resource | Change | Verification |
| --- | --- | --- |
| Render PostgreSQL `hdm-crm-staging-db` | Removed public inbound access after owner confirmed there are no external consumers. | Console reports all internet traffic blocked. Live API database checks still pass over the private connection. |
| S3 `hdm-crm-staging-queue` | Enabled `hdm-crm-media-noncurrent-30-days`, scoped to `media/`, deleting noncurrent versions after 30 days. | Rule detail shows Enabled and Day 30. No expiration of current versions. |
| Shared group `hdm-crm-staging-core` | Corrected `RM_ORG_CLOSURE_ENABLED` and `RM_ORG_PURGE_ENABLED` to `CRM_ORG_CLOSURE_ENABLED` and `CRM_ORG_PURGE_ENABLED`, preserving `true`. | Saved with **Save only**; new names and values verified. Running backend already reports both true through code defaults. |
| Render Web | Removed unused duplicate `UBLIC_DJANGO_API_URL`. Preserved correctly named public and internal API URLs. | Saved with **Save only**; correct variables remain. |

S3 lifecycle processing is asynchronous. The 30 days start when a version becomes
noncurrent, not when the rule was enabled. The previous proposed JSON remains a
historical proposal; the applied rule is recorded separately in
`s3-noncurrent-retention.applied-2026-10-16.json`. The applied rule does not include
the proposal's expired-delete-marker action.

## Live verification

- API `/healthz/` and Web `/login` returned HTTP 200. The API health endpoint alone
  is shallow; dependency checks below were also executed inside the running API.
- `check_hosted_config` passed, including production settings and database role
  constraints. `migrate --check` found no unapplied migrations. Django system
  checks reported no issues.
- Redis cache, Celery broker and result backend each responded to ping.
- Worker logs show successful scheduled reminder, Google scheduling, web-form
  email retry and attachment-cleanup tasks. This does not establish that an actual
  customer's Google sync or reminder was exercised.
- One scheduler instance is configured. Organization purge remains daily at
  04:00 UTC; other schedules were not changed.
- Render could list the `media/` prefix in S3 (HTTP 200). A generic bucket-head
  probe returned 403 because IAM listing is prefix-restricted; no permissions
  were widened to accommodate that unnecessary probe. Upload/download/delete
  were not exercised against production files.
- System Gmail credentials refreshed successfully. Exactly one authorized test
  email to `info@highdemandmedia.com`, subject **Prueba de preparación HDM CRM**,
  returned `TEST_EMAIL_ACCEPTED 1`. The owner confirmed inbox receipt in this
  session. No customer records were created for this test.

## Observed infrastructure

- PostgreSQL 16 is on the paid 256 MB / 1 GB plan, about 10.09% storage used.
  Recovery shows a three-day PITR window and an enabled Restore button. No restore
  drill was performed. Console export retention is at least seven days; no export
  was created during this review.
- Valkey is paid, 256 MB, with Journal + Snapshot persistence, `noeviction`, and
  public inbound traffic blocked.
- API, Web, Worker and Scheduler use paid 512 MB instances. No load test or
  capacity guarantee was performed; no plan was upgraded.
- S3 has Block Public Access enabled, Bucket owner enforced ownership, versioning
  enabled and SSE-S3 encryption. The application's IAM user has no console login;
  its object permissions are limited to this bucket's `media/` prefix.
- AWS root MFA is enabled and no active root access keys were shown.
- Password self-registration remains disabled. Opening to customers continues to
  mean invitation-only access.

## Manual deployment handoff

At inspection, Web was Live on `49078aa`; API, Worker and Scheduler were Live on
`9170edb`. The newer commit is frontend-only, so this does not indicate missing
backend changes. Auto-deploy is off.

To load the saved environment changes, manually deploy API, wait for Live, then
Worker, Scheduler and Web. API already has `sh bin/release.sh` as its pre-deploy
command; do not run migrations concurrently on the other services. No database,
Valkey or AWS redeploy is needed. Network and S3 lifecycle changes are already
effective independently of application deployment.

The uncommitted local email composer/reader and profile changes are not part of
these deployed commits. Review, test and commit them separately before expecting
them online.

## Remaining release checks

1. Test a real invitation and the invited user's setup flow with an explicitly
   authorized test recipient; the standalone email test was received successfully.
2. Complete Google OAuth verification separately. Successful system-email
   authentication does not establish verification of customers' Gmail/Calendar
   scopes; Google Cloud approval was not checked in this Render/AWS review.
3. `CRM_LEGAL_VERSION` is empty at runtime. Versioned acceptance enforcement and
   recording are therefore disabled. Configure it only with the matching approved
   document version; do not invent a version or treat document display as consent.
4. Perform an isolated backup restoration exercise, with external jobs and mail
   disabled, before making recovery-time claims. This requires a separate test
   environment and may incur charges.
5. Validate attachment upload/download and customer workflows end to end. Code
   inspection also found that the protected-route allowlist redirects
   `/record-delete/...` to `/` before its endpoint runs. Track this application
   defect separately; production records were not deleted to reproduce it.

## Follow-up hardening

- No AWS budgets were configured in the inspected account; agree a budget and
  alert destination before creating one.
- The observed Web response lacks CSP, HSTS and X-Frame-Options. Evaluate these
  against the existing frontend and integrations before deploying header changes.
- Monitor failed/overdue organization purges, queue backlog, storage growth and
  delivery errors. Service failure notifications alone do not establish coverage
  for failed background jobs.
- `docs/self-hosting/production-deploy.md` contains legacy deployment guidance;
  use the current Render release instructions until it is reconciled.

## Evidence

Screenshots are in the workspace's
`deliverables/cloud-readiness-2026-10-16/`: `render-db-private.png`,
`s3-retention-active.png`, `render-closure-flags.png`, `render-web-env.png`,
and `render-email-test.png`. No credentials were included in this report.

Provider references: [Render backups](https://render.com/docs/postgresql-backups),
[Render Key Value](https://render.com/docs/key-value),
[S3 lifecycle expiration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-expire-general-considerations.html).
