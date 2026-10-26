from django.db import migrations


def update_keys(apps, schema_editor):
    # Only the derived search index changes. Historical phone text is retained.
    import re

    connection = schema_editor.connection
    alias = connection.alias
    Org = apps.get_model("common", "Org")
    Contact = apps.get_model("contacts", "Contact")
    postgres = connection.vendor == "postgresql"
    # The release role is subject to RLS, just like application requests.
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
                batch = []
                for contact in (
                    Contact.objects.using(alias)
                    .filter(org_id=org_id)
                    .only("id", "phone")
                    .iterator(chunk_size=500)
                ):
                    raw = str(contact.phone or "").strip()
                    digits = re.sub(r"[^0-9]", "", raw)
                    if raw.startswith("00"):
                        digits = digits[2:]
                    elif not raw.startswith("+") and len(digits) == 10:
                        digits = "1" + digits
                    contact.phone_match_key = digits
                    batch.append(contact)
                    if len(batch) == 500:
                        Contact.objects.using(alias).bulk_update(
                            batch, ["phone_match_key"], batch_size=500
                        )
                        batch.clear()
                if batch:
                    Contact.objects.using(alias).bulk_update(
                        batch, ["phone_match_key"], batch_size=500
                    )
        finally:
            if postgres and not connection.needs_rollback:
                cursor.execute(
                    "SELECT set_config('app.current_org', %s, true)", [previous]
                )


class Migration(migrations.Migration):
    dependencies = [("contacts", "0022_contact_merge_archive")]
    operations = [migrations.RunPython(update_keys, migrations.RunPython.noop)]
