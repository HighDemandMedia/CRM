# Compact business identifiers

Organizations use `HDM-` plus eight cryptographically random Crockford Base32
characters. Business records use `USR`, `CON`, `COM`, `DEA`, `TSK`, `TKT`, or `EVT`
plus a global per-type sequence, padded to at least four digits. Sequences expand
past 9999 and are not reset when records are deleted. These are real primary keys,
not display labels. Global sequences are necessary because each model has one
primary-key column shared by all tenants.

Auxiliary rows (memberships, roles, stages, notes, files, mail activities, etc.)
retain their UUID primary keys. Their foreign keys follow the migrated business
records. Authentication, OAuth, invitation, reset, and idempotency tokens retain
their existing cryptographic generation and validation. An ID is not permission
to access a record; organization isolation and action permissions still apply.

`BusinessIDField` allocates on insertion, including bulk insertion, without
consuming IDs for form/import previews. Database row locks serialize allocation.
Organization reservations prevent reuse after deletion. `LegacyBusinessID`
resolves old links, signed-session claims, and queued references to the new keys;
it does not retain copies of business records or credentials.

## Migration and release constraints

`common.0085_compact_business_ids` updates all eight models, incoming foreign
keys, join tables, generic references, and structured JSON references atomically.
It captures existing PostgreSQL row policies, disables them only inside that
transaction while changing dependent columns, then recreates them and restores
their enabled/forced state before committing. Failure rolls back the transaction.
The migration requires ownership of the affected tables and locks them during
schema changes. It preserves file keys, email contents, provider IDs, and secrets.

Before applying on an environment:

1. Take and verify a database backup.
2. Quiesce API writes and stop that environment's workers/scheduler. Do not run
   old application code against the new schema.
3. Apply the migration with the same application revision as the services.
4. Verify counts, associations, policies, and permissions; then start services.
5. Check record links, current sessions, webforms, imports/exports, and queues.

The data conversion is deliberately irreversible through `migrate`. Restore the
pre-change database backup **and matching application code** to roll back.
External clients should use returned IDs instead of assuming UUIDs. Ordinary
old record/webform URLs resolve through the mapping. Previously issued security
tokens are never rewritten; a password-reset link whose validation binds the
old primary key may require requesting a new link.

Production migration and release require explicit authorization and the checks
above. Existing organizations and records are migrated in place; no account reset
or data deletion is part of this migration.
