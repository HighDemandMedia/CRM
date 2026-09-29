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
