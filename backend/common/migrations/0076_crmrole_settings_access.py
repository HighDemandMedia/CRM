from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("common", "0075_gmail_send_operations")]
    operations = [
        migrations.AddField(
            model_name="crmrole",
            name="settings_access",
            field=models.JSONField(default=dict, blank=True),
        ),
    ]
