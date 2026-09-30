from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("webforms", "0003_webform_contact_source_webform_notify_email_and_more")
    ]
    operations = [
        migrations.AddField(
            model_name="webform",
            name="connection_mode",
            field=models.CharField(
                max_length=16,
                choices=[("new", "Create form"), ("existing", "Connect existing form")],
                default="existing",
            ),
        ),
        migrations.AddField(
            model_name="webform",
            name="website_form_id",
            field=models.CharField(max_length=128, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="webform",
            name="appearance",
            field=models.JSONField(default=dict, blank=True),
        ),
    ]
