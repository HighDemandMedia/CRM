# Page-load optimization — September 28, 2026

This change targets navigation on the hosted Render application. AWS S3 remains the attachment store; no bucket or infrastructure changes are required.

## Changes

- One JWT-authenticated `/api/org/ui-context/` request replaces four shell configuration requests. It returns current permissions, terminology, property ordering and pipeline definitions. Responses are private and not cached.
- Navigation counters stream after the required configuration. Their failure or latency does not block the record page.
- Company records and shell configuration load concurrently.
- Companies, contacts and deals request compact list responses. Detail endpoints retain their full payloads. List responses preserve the fields used by rows/cards and the existing permission filters, but omit unused detail panels and full nested records.
- Company and deal pipeline columns omit repeated picker catalogues.

## Measurements and validation

The backend comparison used eight companies, eight contacts and eight deals with linked records in an isolated SQLite test database. These are query/payload measurements, not promised online load times.

| List | SQL queries before → after | Response bytes before → after |
| --- | ---: | ---: |
| Companies | 107 → 15 | 24,721 → 15,406 |
| Deals | 434 → 19 | 57,243 → 9,843 |
| Contacts | 15 → 15 | 22,500 → 21,204 |

Nine backend regression tests cover payload equivalence, fresh settings, tenant boundaries, own-record permissions including nested relations, authentication, and the reductions above. Five frontend tests cover nonblocking counters, counter failures, configuration errors and concurrent company loading.

The production frontend build and Svelte checks pass. A production-build smoke check against a synthetic local API delayed the optional counter by 1.5 seconds: company HTML arrived in 48 ms, before the counter completed. This verifies streaming behavior, not Render performance.

The broader runs passed 299 backend tests and 686 frontend tests, with three backend and four frontend failures reproduced separately on the unchanged baseline commit `2ac431b`. Those existing failures concern closed-deal field requirements, contact history and stage validation expectations. Two further backend tests and one frontend test were added afterwards; the complete targeted suites pass. PostgreSQL RLS policies were not changed; these SQLite tests do not validate database-level RLS enforcement.

## Deployment order

1. Deploy the latest commit to **hdm-crm-staging-api**. Wait for Live and a successful health check.
2. Deploy the same commit to **hdm-crm-staging-web**. The new web build requires the new UI context endpoint, so deploy the API first.
3. Reload `https://crm.highdemandmedia.com` and compare Contacts, Companies and Deals list/pipeline navigation with the same account and filters.
4. Check one restricted user and one organization administrator. Confirm record visibility, custom properties, stages and counters.

No migration, new environment variable, S3 change, worker restart or scheduler restart is required by this change. If rollback is needed, roll back the web service first; the optimized API still supports the previous web build.

Authenticated online navigation still needs verification after deployment. If it remains slow, correlate browser request timings with Render API latency, CPU/memory and database query timings before changing hosting plans. The public login page and API health endpoint alone do not represent authenticated list performance.

## September 29: batched boards and private server requests

The hosted audit confirmed that API and web run on 0.5 CPU / 512 MB paid instances, both deployed at `a2d5056`. Available CPU/memory graphs did not show sustained saturation. PostgreSQL remained Free; its CPU/connections telemetry was unavailable, so database saturation was not established. Point-in-time automated authenticated navigation measured about 1.4 s for Contacts and 0.7 s for Companies/Deals list views. These are not load-test results.

### Batched board contract

Contacts, companies and deals accept `board=true` on their existing list endpoint. Existing authentication, record scopes and all list filters run before building columns. `limit` (default 25, maximum 100) applies independently to every configured stage; `<stage>_offset` is clamped to 0–10,000,000. SQL selects only that page of IDs per column, followed by one shared serializer/prefetch batch. Empty columns remain present. Counts and currency-separated amounts cover all matching records, not just the page. Contact totals still count a shared visible deal only once per column/header.

The frontend makes one board request instead of an initial list plus one request per stage. The previous read path is retained as a fallback only if an older API returns no `board` field during rollout. Tasks and tickets already use their existing board endpoints and are unchanged.

Local regression data used three matching records per configured stage, one extra custom stage, limit 2, and an offset in one column. Compared with the previous per-column reads (excluding their additional initial header request):

| Board | Admin SQL before → after | Own-record scope before → after |
| --- | ---: | ---: |
| Companies | 96 → 25 | 114 → 38 |
| Contacts | 108 → 28 | 126 → 41 |
| Deals | 126 → 30 | 147 → 45 |

The ten board tests pass against SQLite and PostgreSQL under a non-superuser/non-BYPASSRLS role. They compare row payloads, custom stages, per-column pagination, filtered totals, own-record visibility, cross-organization isolation, empty columns and authentication. The 23-test SQLite run also includes existing UI-context and currency-total regressions. The frontend passes 25 targeted tests (board loads, rolling-deploy fallback, private/public origins, file streaming and sign-in/session handling), Svelte checks with zero errors/warnings, and the production build.

### Private networking rollout

1. Deploy the API commit. No migration is required.
2. In the API service's `ALLOWED_HOSTS`, retain the existing public host and append `hdm-crm-staging-api` (no scheme or port).
3. On **web only**, set `DJANGO_INTERNAL_API_URL=http://hdm-crm-staging-api:10000`, the Internal Address verified in Render's Connect menu. Keep `PUBLIC_DJANGO_API_URL=https://hdm-crm-staging-api.onrender.com` and the web's HTTPS `ORIGIN` unchanged.
4. Deploy web, verify signed-in lists/boards and API logs. The browser still uses HTTPS. Server-only fetches, authentication and downloads use the private route; form-embed and organization-settings requests retain the public origin because their responses generate public absolute URLs.
5. Compare with the same account/filters after deployment. SQL reductions do not promise a particular online response time. Revert the web's private variable (empty/unset) to fall back to the public route if necessary.

No paid plan change, database connection-pool change, S3 change, worker or scheduler restart is needed. The private hostname is never included in page data or client bundles.
