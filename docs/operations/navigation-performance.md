# Navigation performance

People/filter catalogues live in module layouts. Tasks and ordinary Tickets queries inherit them directly instead of calling server `parent()`, which re-executes server ancestor loads even when their browser data is retained. Contacts, Companies, Deals and the open-stage Tickets preset still need parent pipeline configuration and can repeat those catalogue requests. Organization/session changes must continue to invalidate layouts; do not replace this with a shared server cache. Record authorization is checked by the API on every request.

Stage updates invalidate only `crm:contacts`, `crm:companies` or `crm:deals`. Changes to people/tags can invalidate `crm:contact-options` or `crm:deal-options`; broad mutations still invalidate all data.

Tasks/Tickets options expose `crm:task-options` / `crm:ticket-options`; Tickets requests compact tags. Hidden Tickets counters are skipped outside Analytics/Approvals. Notifications coalesce navigation/focus refreshes for 15 seconds, but opening the panel/read mutations refresh immediately and visible polling remains 45 seconds.

The stage-requirement editor loads dynamically to keep international phone validation out of the shell's static import graph. Creation panels open with a loading state, discard late results after cancellation, and keep errors retryable. List navigation links resolve saved sorting before navigation/preload; direct bare-URL entry retains the existing preference fallback. See `../audits/2026-10-26-performance-improvements.md` for measurements and limitations.

Contact edit options load from the private, non-cacheable `/api/contact-editor/[id]` route only when Edit is opened. Emails stay mounted after their first visit; returning after 60 seconds refreshes them. Leaving the record destroys this state.

## API connection pool

For the current API with one process/two threads, use service-local variables:

```text
DB_POOL_ENABLED=true
DB_POOL_MIN_SIZE=1
DB_POOL_MAX_SIZE=2
```

Keep `CONN_MAX_AGE=0` and the existing `reset_rls_context` callback. Never enable a pool without tenant-context reset. Do not put these settings in the shared environment group: Celery has a separate process/concurrency budget. Recalculate the connection budget before increasing workers. Rollback: set `DB_POOL_ENABLED=false` and redeploy the API.

Verified locally: pool reuse with Django, PostgreSQL pool reset/isolation tests, middleware exception reset tests, API permission/pipeline regressions, frontend tests, type checks and build. Production timings must be measured on the same account and browser before/after; local development timing is not comparable.
