from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("common", "0085_compact_business_ids")]

    operations = [
        migrations.AddField(
            model_name="googleconnection",
            name=name,
            field=models.CharField(max_length=length, blank=True, db_default=""),
        )
        for name, length in (
            ("oauth_client_id", 255),
            ("oauth_project_id", 128),
            ("pending_client_id", 255),
            ("pending_project_id", 128),
        )
    ]
