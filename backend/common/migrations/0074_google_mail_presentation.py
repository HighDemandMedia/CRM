from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("common", "0073_profile_setup_step")]
    operations = [
        migrations.AddField(
            model_name="googleconnection",
            name="mail_contacts_fingerprint",
            field=models.CharField(max_length=64, blank=True),
        ),
        migrations.AddField(
            model_name="googlemailactivity",
            name="cc",
            field=models.JSONField(default=list),
        ),
    ]
