# Navigation performance

Contacts and Deals retain people/filter catalogues in route layouts. Query changes reload records, not those catalogues. Organization/session changes must continue to invalidate layouts; do not replace this with a shared server cache. Record authorization is checked by the API on every request.

Stage updates invalidate only `crm:contacts`, `crm:companies` or `crm:deals`. Changes to people/tags can invalidate `crm:contact-options` or `crm:deal-options`; broad mutations still invalidate all data.

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
