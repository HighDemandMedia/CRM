from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("common", "0070_unique_attachment_storage_keys")]
    operations = [
        migrations.AddField(
            model_name="organizationinvitation",
            name="grants_ownership",
            field=models.BooleanField(default=False, editable=False),
        )
    ]
