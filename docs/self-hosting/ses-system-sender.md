# Amazon SES system sender

SES handles CRM transactional mail only: invitations, password recovery,
enabled notifications, assignments, appointments and web-form confirmations.
It does not replace Google sign-in or personal Gmail/Calendar connections.
Templates, recipients, attachments and Reply-To continue through Django's
existing mail composition and background tasks.

## Prepare without interrupting delivery

1. Keep the current `EMAIL_BACKEND` and all `GMAIL_SYSTEM_*` values unchanged.
2. Verify the sending identity, DKIM and custom MAIL FROM in the intended SES
   region. Preserve the root MX and SPF records used by Google Workspace.
3. Request production access for transactional mail. Sandbox access cannot send
   to arbitrary customer addresses, even when the sending domain is verified.
4. Keep bounce/complaint email feedback and account-level suppression enabled.
   The operator must monitor feedback and stop retries to suppressed recipients.
5. Create a dedicated sender with no console login, S3, IAM or administrative
   permissions. Generate the IAM baseline from the installed django-ses runtime
   using IAM Policy Autopilot, then review resource scope before applying it.
   The current SES v1 path needs `ses:SendRawEmail` on the verified domain identity
   and `ses:GetSendQuota` for django-ses throttling. Restrict From to the actual
   system sender. Review again if switching to SES v2 or configuration sets.
6. Store dedicated mail credentials in a private Render environment group used
   only by API, Worker and Scheduler. Never place them in Web, Git, screenshots
   or chat. Do not replace the existing S3 access keys.

## Backend environment at cutover

```dotenv
EMAIL_BACKEND=django_ses.SESBackend
AWS_SES_REGION_NAME=us-east-1
AWS_SES_REGION_ENDPOINT=email.us-east-1.amazonaws.com
DEFAULT_FROM_EMAIL=High Demand Media CRM <info@highdemandmedia.com>
```

Set `AWS_SES_ACCESS_KEY_ID` and `AWS_SES_SECRET_ACCESS_KEY` privately. Both must
belong to the dedicated SES sender. Do not use SMTP credentials for this API
backend. Leave `AWS_SES_CONFIGURATION_SET` empty unless that set exists in the
same region and its use is allowed by the sender policy. An absent credential
pair preserves django-ses's existing credential chain for other installations;
HDM must explicitly configure the separate pair before cutover.

## Activation gates

- AWS shows production access enabled, sending enabled, and a suitable sending
  quota/rate for all API and worker processes combined. django-ses throttling is
  per process, not a distributed rate limiter.
- Run `python manage.py check_hosted_config` with the candidate configuration.
  This validates static settings; it does not prove AWS permissions or delivery.
- With the new credentials and before changing the default backend, send one
  explicitly authorized canary from the actual Render runtime using a temporary
  SES connection. Confirm arrival and SPF/DKIM in the receiving mailbox.
- Deploy the reviewed code before activating new settings. Switch API, Worker
  and Scheduler together, preserving queued jobs and the old Google credentials.
  No frontend deployment is needed for SES-only changes.
- Verify a controlled transactional workflow, recipient, HTML/text, links and
  calendar attachment. Check worker errors and SES bounce/complaint metrics.

The SES console canary proves DNS and SES-to-mailbox delivery only. It does not
prove Render's IAM credentials or the CRM-to-SES connection.

## Rollback

Restore `EMAIL_BACKEND=common.gmail_backend.GmailEmailBackend` on the backend
services and redeploy/restart them with the unchanged `GMAIL_SYSTEM_*` settings.
Do not replay an uncertain send automatically: AWS may have accepted it even if
the response was lost, so retrying through Google can send duplicates. Inspect
the delivery outcome first. Retire the old system-mail Google token only after
the SES cutover is stable and separately authorized.

## HDM verification — 2026-10-28

- Identity `highdemandmedia.com`, region `us-east-1`: Verified.
- Easy DKIM RSA 2048 and `crm-mail.highdemandmedia.com` MAIL FROM: Successful.
- Production access granted in us-east-1 on 2026-10-28; console shows
  50,000 emails per 24 hours and 14 emails per second.
- Email feedback: enabled. Account suppression: bounce and complaint enabled.
- One authorized console email delivered to `info@highdemandmedia.com`;
  Gmail headers confirm SPF pass and domain DKIM pass, with custom MAIL FROM.
- No DMARC record was found during the DNS audit. Add a reviewed monitoring
  policy separately; the test does not establish DMARC policy enforcement.
- IAM user `hdm-crm-ses-sender` created with console access disabled and only
  `HDMCRMTransactionalMail` attached directly. Verified policy allows
  `ses:SendRawEmail` for the domain identity with From restricted to
  `info@highdemandmedia.com`, plus `ses:GetSendQuota`. The owner subsequently
  reported creating credentials and saving them privately in Render.
- Render group `hdm-crm-ses-mail` (evg-dbh3rog473hc73d9b1j0) verified with
  all four expected variable names, us-east-1 region and matching endpoint, and
  zero linked services. Credential values were not revealed or authenticated.
- Render mail provider remains unchanged. Deploying the reviewed code, linking
  credentials, and an authorized canary from Render remain activation gates.

References: [SES production access](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html),
[IAM sender restrictions](https://docs.aws.amazon.com/ses/latest/dg/control-user-access.html),
[email feedback](https://docs.aws.amazon.com/ses/latest/dg/monitor-sending-activity-using-notifications-email.html).
