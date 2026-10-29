from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [("common", "0086_google_oauth_client_provenance")]
    operations = [
        *[
            migrations.AddField(
                model_name="googleconnection",
                name=name,
                field=models.DateTimeField(null=True, blank=True),
            )
            for name in (
                "mail_sync_requested_at",
                "mail_watch_expires_at",
                "mail_watch_renewed_at",
            )
        ],
        migrations.AddField(
            model_name="googleconnection",
            name="mail_watch_topic",
            field=models.CharField(max_length=255, blank=True, db_default=""),
        ),
        migrations.AddField(
            model_name="googlemailactivity",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
    ]
