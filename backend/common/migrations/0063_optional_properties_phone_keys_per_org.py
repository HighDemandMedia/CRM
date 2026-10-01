"""Backfill with tenant context so PostgreSQL RLS also sees existing records."""

import re

from django.db import migrations


def backfill_per_org(apps, schema_editor):
    connection = schema_editor.connection
    alias = connection.alias
    Org = apps.get_model("common", "Org")
    Contact = apps.get_model("contacts", "Contact")
    Definition = apps.get_model("common", "CustomFieldDefinition")
    postgres = connection.vendor == "postgresql"
    with connection.cursor() as cursor:
        previous = ""
        if postgres:
            cursor.execute("SELECT current_setting('app.current_org', true)")
            previous = cursor.fetchone()[0] or ""
        try:
            for org_id in (
                Org.objects.using(alias).values_list("pk", flat=True).iterator()
            ):
                if postgres:
                    cursor.execute(
                        "SELECT set_config('app.current_org', %s, true)", [str(org_id)]
                    )
                Definition.objects.using(alias).filter(
                    org_id=org_id,
                    target_model__in=[
                        "Contact",
                        "Account",
                        "Opportunity",
                        "Task",
                        "Case",
                    ],
                    is_required=True,
                ).update(is_required=False)
                batch = []
                for contact in (
                    Contact.objects.using(alias)
                    .filter(org_id=org_id)
                    .only("id", "phone")
                    .iterator(chunk_size=500)
                ):
                    digits = re.sub(r"[^0-9]", "", contact.phone or "")
                    contact.phone_match_key = (
                        digits[2:] if digits.startswith("00") else digits
                    )
                    batch.append(contact)
                    if len(batch) == 500:
                        Contact.objects.using(alias).bulk_update(
                            batch, ["phone_match_key"], batch_size=500
                        )
                        batch = []
                if batch:
                    Contact.objects.using(alias).bulk_update(
                        batch, ["phone_match_key"], batch_size=500
                    )
        finally:
            if postgres:
                cursor.execute(
                    "SELECT set_config('app.current_org', %s, true)", [previous]
                )


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0062_optional_crm_properties"),
        ("contacts", "0021_required_record_names"),
    ]
    operations = [migrations.RunPython(backfill_per_org, migrations.RunPython.noop)]
