"""Frozen migration machinery: convert the business graph in one transaction.

UUID auxiliary records and credential/token identifiers are not renumbered.
Rollback requires restoring the pre-migration database backup.
"""

import json
import secrets

from django.db import migrations, models
from django.db.migrations.exceptions import IrreversibleError

TARGETS = {
    "common.org": "HDM",
    "common.user": "USR",
    "contacts.contact": "CON",
    "accounts.account": "COM",
    "opportunity.opportunity": "DEA",
    "tasks.task": "TSK",
    "cases.case": "TKT",
    "common.salesappointment": "EVT",
}


def replace_json(value, mapping):
    if isinstance(value, str):
        return mapping.get(value, value)
    if isinstance(value, list):
        return [replace_json(item, mapping) for item in value]
    if isinstance(value, dict):
        return {
            mapping.get(key, key): replace_json(item, mapping)
            for key, item in value.items()
        }
    return value


def renumber(apps, editor):
    connection = editor.connection
    q = editor.quote_name
    mapping = {}
    sequences = apps.get_model("common", "BusinessIDSequence")
    reservations = apps.get_model("common", "OrganizationIDReservation")
    legacy = apps.get_model("common", "LegacyBusinessID")
    all_models = list(apps.get_models(include_auto_created=True))
    with connection.cursor() as cursor:
        for label, prefix in TARGETS.items():
            model = apps.get_model(label)
            table, pk = q(model._meta.db_table), q(model._meta.pk.column)
            cursor.execute(f"SELECT {pk} FROM {table} ORDER BY {pk}")
            rows = cursor.fetchall()
            for number, (old,) in enumerate(rows, 1):
                if prefix == "HDM":
                    while True:
                        new = "HDM-" + "".join(
                            secrets.choice("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
                            for _ in range(8)
                        )
                        _, created = reservations.objects.using(
                            connection.alias
                        ).get_or_create(pk=new)
                        if created:
                            break
                else:
                    new = f"{prefix}-{number:04d}"
                old = str(old)
                if old in mapping:
                    raise RuntimeError(
                        "Ambiguous legacy identifier; migration rolled back."
                    )
                mapping[old] = new
            sequences.objects.using(connection.alias).update_or_create(
                prefix=prefix, defaults={"last_number": len(rows)}
            )

        legacy.objects.using(connection.alias).bulk_create(
            [legacy(id=old, replacement=new) for old, new in mapping.items()],
            batch_size=1000,
        )

        # Deferred FK checks let the entire connected graph move together.
        if connection.vendor == "postgresql":
            cursor.execute("SET CONSTRAINTS ALL DEFERRED")
            cursor.execute(
                "CREATE TEMP TABLE crm_id_map (old_id text PRIMARY KEY, new_id text NOT NULL) ON COMMIT DROP"
            )
            cursor.executemany(
                "INSERT INTO crm_id_map VALUES (%s, %s)", list(mapping.items())
            )
        for model in all_models:
            for field in model._meta.local_fields:
                target = field.remote_field.model if field.is_relation else None
                is_target = target is not None and target._meta.label_lower in TARGETS
                is_pk = field.primary_key and model._meta.label_lower in TARGETS
                is_generic = (model._meta.label_lower, field.name) in {
                    ("admin.logentry", "object_id"),
                    ("common.comment", "object_id"),
                    ("common.attachments", "object_id"),
                    ("common.activity", "entity_id"),
                    ("common.notification", "entity_id"),
                    ("common.portalaccesstoken", "resource_id"),
                    ("common.organizationclosure", "org_id"),
                    ("common.organizationlifecycleevent", "org_id"),
                    ("common.organizationlifecycleevent", "actor_id"),
                    ("common.pendingfiledeletion", "org_id"),
                }
                if is_target or is_pk or is_generic:
                    if connection.vendor == "postgresql":
                        cursor.execute(
                            f"UPDATE {q(model._meta.db_table)} AS target SET {q(field.column)} = mapping.new_id FROM crm_id_map AS mapping WHERE target.{q(field.column)} = mapping.old_id"
                        )
                    else:
                        sql = f"UPDATE {q(model._meta.db_table)} SET {q(field.column)} = %s WHERE {q(field.column)} = %s"
                        cursor.executemany(
                            sql, [(new, old) for old, new in mapping.items()]
                        )

        # Saved views, histories, and integration metadata use JSON references.
        for model in all_models:
            for field in model._meta.local_fields:
                if not isinstance(field, models.JSONField):
                    continue
                table, pk, column = map(
                    q, (model._meta.db_table, model._meta.pk.column, field.column)
                )
                cursor.execute(
                    f"SELECT {pk}, {column} FROM {table} WHERE {column} IS NOT NULL"
                )
                for key, raw in cursor.fetchall():
                    value = json.loads(raw) if isinstance(raw, str) else raw
                    changed = replace_json(value, mapping)
                    if changed != value:
                        cursor.execute(
                            f"UPDATE {table} SET {column} = %s WHERE {pk} = %s",
                            [json.dumps(changed), key],
                        )
        if connection.vendor == "postgresql":
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")


class CompactBusinessIDs(migrations.operations.base.Operation):
    """Coordinate cross-app state and DB changes without an intermediate release."""

    reduces_to_sql = False
    reversible = False

    def __init__(self, changes):
        self.changes = changes

    def state_forwards(self, app_label, state):
        for label, operation in self.changes:
            operation.state_forwards(label, state)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        connection = schema_editor.connection
        q = schema_editor.quote_name
        policies, tables = [], []
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT tablename, policyname, permissive, roles, cmd, qual, with_check FROM pg_policies WHERE schemaname = current_schema()"
                )
                policies = cursor.fetchall()
                cursor.execute(
                    "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class JOIN pg_namespace ON pg_namespace.oid = relnamespace WHERE nspname = current_schema() AND relkind = 'r' AND relrowsecurity"
                )
                tables = cursor.fetchall()
                for table, _, _ in tables:
                    cursor.execute(f"ALTER TABLE {q(table)} DISABLE ROW LEVEL SECURITY")
                for table, name, *_ in policies:
                    cursor.execute(f"DROP POLICY {q(name)} ON {q(table)}")
        state = from_state.clone()
        for label, operation in self.changes:
            previous = state.clone()
            operation.state_forwards(label, state)
            operation.database_forwards(label, schema_editor, previous, state)
        # CreateModel queues FK SQL; flush it before moving the graph.
        for statement in schema_editor.deferred_sql:
            schema_editor.execute(statement)
        schema_editor.deferred_sql.clear()
        renumber(to_state.apps, schema_editor)
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                for table, name, permissive, roles, command, using, check in policies:
                    role_sql = ", ".join(
                        "PUBLIC" if role == "public" else q(role) for role in roles
                    )
                    sql = f"CREATE POLICY {q(name)} ON {q(table)} AS {permissive} FOR {command} TO {role_sql}"
                    if using:
                        sql += f" USING ({using})"
                    if check:
                        sql += f" WITH CHECK ({check})"
                    cursor.execute(sql)
                for table, enabled, forced in tables:
                    if enabled:
                        cursor.execute(
                            f"ALTER TABLE {q(table)} ENABLE ROW LEVEL SECURITY"
                        )
                    if forced:
                        cursor.execute(
                            f"ALTER TABLE {q(table)} FORCE ROW LEVEL SECURITY"
                        )

    def database_backwards(self, *args, **kwargs):
        raise IrreversibleError("Restore the database backup taken before compact IDs.")

    def describe(self):
        return "Replace business UUID keys and references atomically with compact IDs"
