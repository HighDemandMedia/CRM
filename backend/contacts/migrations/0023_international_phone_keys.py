from django.db import migrations


def update_keys(apps, schema_editor):
    # Only the derived search index changes. Historical phone text is retained.
    import re

    Contact = apps.get_model("contacts", "Contact")
    batch = []
    for contact in (
        Contact.objects.using(schema_editor.connection.alias)
        .all()
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
            Contact.objects.using(schema_editor.connection.alias).bulk_update(
                batch, ["phone_match_key"]
            )
            batch.clear()
    if batch:
        Contact.objects.using(schema_editor.connection.alias).bulk_update(
            batch, ["phone_match_key"]
        )


class Migration(migrations.Migration):
    dependencies = [("contacts", "0022_contact_merge_archive")]
    operations = [migrations.RunPython(update_keys, migrations.RunPython.noop)]
