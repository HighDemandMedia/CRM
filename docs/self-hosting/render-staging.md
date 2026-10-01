# High Demand Media CRM: Render staging

This is the deployment plan for the first online tester environment. Creating
environment groups does not deploy a service or verify its credentials.

## Existing infrastructure

- Render project: High Demand Media CRM, environment: Staging, region: Virginia.
- PostgreSQL 16: use the existing database; do not create another via Blueprint.
- Key Value: existing staging instance, eviction policy `noeviction`.
- Private S3 bucket: `hdm-crm-staging-queue`, region `us-east-1`, prefix `media/`.
- System email: authorized Gmail mailbox `info@highdemandmedia.com`.
- Intended frontend domain: `crm.highdemandmedia.com` (Squarespace DNS).

## Environment groups

Keep database and email secrets out of frontend services and out of Git.

### hdm-crm-staging-storage (already created manually)

`AWS_BUCKET_NAME`, `AWS_S3_REGION_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`.

### hdm-crm-staging-mail (already created manually)

`EMAIL_BACKEND=common.gmail_backend.GmailEmailBackend`, `DEFAULT_FROM_EMAIL`,
`GMAIL_SYSTEM_SENDER`, `GMAIL_SYSTEM_CLIENT_ID`, `GMAIL_SYSTEM_CLIENT_SECRET`,
`GMAIL_SYSTEM_REFRESH_TOKEN`. See [Gmail sender](gmail-system-sender.md).

### hdm-crm-staging-core (create before backend services)

| Variable | Value |
| --- | --- |
| DBHOST | PostgreSQL internal hostname from Render |
| DBPORT | PostgreSQL port from Render, normally 5432 |
| DBNAME | Database name from Render |
| DBUSER | PostgreSQL username from Render |
| DBPASSWORD | PostgreSQL password from Render |
| CELERY_BROKER_URL | Key Value internal connection URL |
| CELERY_RESULT_BACKEND | Same Key Value internal connection URL |
| CACHE_URL | Shared Key Value internal connection URL; required for hosted rate limits and caches |
| SECRET_KEY | Generate a private random value of at least 50 bytes |
| ENV_TYPE | prod (runtime security mode; this remains the Staging environment) |
| DEBUG | false |
| PASSWORD_REGISTRATION_ENABLED | false |
| CORS_ALLOW_ALL | false |
| TRUST_PROXY_SSL_HEADER | true (Render is the sole public ingress) |
| FRONTEND_URL | Actual frontend HTTPS URL used for this deployment |
| CORS_ALLOWED_ORIGINS | Actual frontend HTTPS URL |
| CSRF_TRUSTED_ORIGINS | Actual frontend HTTPS URL |
| ALLOWED_HOSTS | Actual API hostname(s), comma separated, without https:// |

Do not paste example hostnames into production settings. First reserve/configure
the service names, then use the exact Render-assigned URLs. Switch the three
frontend URL settings and the frontend ORIGIN together when custom DNS is ready.
Leave SESSION_COOKIE_DOMAIN unset so cookies stay host-scoped.

`CACHE_URL` must be available to API, worker and scheduler through the core group.
Use the same Redis database and cache namespace for these services. A cache configured
only on one service is not a shared limit. Remove conflicting service-level overrides
after checking their values. Do not share this cache with an unrelated environment.

## Services (create only after the verified code is pushed)

Use the CRM GitHub repository and `main`, with automatic deploys initially off.
Use Virginia and the existing Staging project environment for every service.
Select the paid service plans explicitly in the dashboard; this guide does not
purchase resources. The API's pre-deploy command requires a paid web service.

| Name | Type | Docker setup | Command |
| --- | --- | --- | --- |
| hdm-crm-staging-api | Web Service | Root context, `Dockerfile`, default runtime stage | Default CMD (`sh bin/start-web.sh`) |
| hdm-crm-staging-worker | Background Worker | Same as API | `sh bin/start-worker.sh` |
| hdm-crm-staging-scheduler | Background Worker | Same as API | `sh bin/start-beat.sh` |
| hdm-crm-staging-web | Web Service | Root directory `frontend`, Dockerfile `Dockerfile` | Default CMD (`node build/index.js`) |

Link core, storage and mail groups to API, worker and scheduler only. For API,
set Pre-Deploy Command to `sh bin/release.sh` and Health Check Path to `/healthz/`.
Migrations run once on API release, not concurrently in the worker/scheduler.
Deploy the API successfully before deploying workers. Run exactly one scheduler.

Frontend variables:
- `PUBLIC_DJANGO_API_URL`: actual HTTPS API origin, no `/api` suffix.
- `ORIGIN`: actual frontend HTTPS origin.
- `NODE_ENV=production`.

Render supplies PORT. Backend startup collects static files into the running
container and serves them with WhiteNoise. API access logs exclude query strings,
which can contain sign-in or integration codes. Runtime runs as a non-root user.
Local Compose keeps the development image stage and its original entrypoint.

## Release checks

The hosted guard refuses development mode, wildcard hosts, open CORS, public
registration, insecure cookies and an HTTP frontend. It rejects a process-local
cache: `CACHE_URL` must select the shared Redis backend. It verifies PostgreSQL is
not using a superuser or BYPASSRLS role and that row_security is on. Migrations
enable/force the policies; this check does not replace tenant-isolation tests.

Do not use `create_default_admin` online. Provision the owner's organization
privately before inviting testers using [private account provisioning](account-provisioning.md); do not temporarily open public registration.
Local users, passwords, organizations and attachments are not uploaded by Git.

Before inviting testers, verify login/recovery, a real Gmail delivery, private
attachment upload/download, worker/scheduler execution and cross-organization
access isolation. Test the frontend and API custom domains and HTTPS after DNS.

Remaining time limits: free Render PostgreSQL expires after 30 days and has no
managed backups; free Key Value loses queued jobs on restart; external Google
OAuth Testing refresh tokens for Gmail expire after seven days. Resolve these
before relying on uninterrupted access. No online deployment is certified by
the local checks alone.

References:
- https://render.com/docs/docker
- https://render.com/docs/deploys
- https://render.com/docs/configure-environment-variables
- https://render.com/docs/free
