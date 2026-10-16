# Platform usage

`/platform-usage` is available in the main sidebar only to an active platform
owner. The API independently checks the current user; organization admins cannot
grant access. Counters run inside each organization's RLS context and are cached
for 60 seconds. Open or refresh the panel to update its measurements.

## Database capacity

- Used: PostgreSQL `pg_database_size(current_database())`, measured on the API's
  database. Local and hosted environments are identified separately.
- Total: operator-maintained `CRM_DATABASE_CAPACITY_BYTES` in the API environment.
  Set it from the hosting provider's allocation; zero means unknown. Update it
  whenever storage is resized. It does not enforce a quota.
- Available (estimated): total minus database size, floored at zero. This is not
  filesystem free space: WAL, logs and other databases are excluded.
- Alerts: 70% plan, 80% expand soon, 90% urgent, computed from unrounded usage.
  Unknown capacity or measurement never produces a healthy/zero-use result.

These are panel alerts, not background notifications or predictive forecasts.
CPU, memory and S3 metrics remain in the linked provider dashboards. No assumed
user or object quotas are imposed.

## Deployment

Deploy API and Web. No migrations, worker changes or scheduler jobs are required.
On 2026-10-16 Render showed a 1 GB allocation for `hdm-crm-staging-db`; API capacity
was configured as `1000000000` bytes. Do not copy this allocation into local demo
configuration. Verify the owner panel against database aggregates after deployment.
