from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("common", "0088_gmail_revision_database_default")]
    operations = [
        migrations.AddField(
            model_name="googleconnection",
            name="calendar_sync_token",
            field=models.TextField(blank=True, db_default=""),
        ),
        *[
            migrations.AddField(
                model_name="googleconnection",
                name=name,
                field=models.DateTimeField(null=True, blank=True),
            )
            for name in (
                "calendar_full_synced_at",
                "calendar_sync_requested_at",
                "calendar_watch_expires_at",
            )
        ],
        *[
            migrations.AddField(
                model_name="googleconnection",
                name=name,
                field=models.CharField(max_length=size, blank=True, db_default=""),
            )
            for name, size in (
                ("calendar_watch_id", 64),
                ("calendar_watch_resource", 1024),
            )
        ],
    ]
