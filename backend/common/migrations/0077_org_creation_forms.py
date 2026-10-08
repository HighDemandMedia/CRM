from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("common", "0076_crmrole_settings_access")]
    operations = [
        migrations.AddField(
            model_name="org",
            name="creation_forms",
            field=models.JSONField(default=dict, blank=True),
        )
    ]
