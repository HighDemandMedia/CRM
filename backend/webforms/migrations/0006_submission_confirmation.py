from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("webforms", "0005_email_delivery_claim")]

    operations = [
        migrations.AddField(
            model_name="webform",
            name="send_confirmation_email",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="webformsubmission",
            name="confirmation_requested",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="webformsubmission",
            name="submission_language",
            field=models.CharField(
                choices=[("en", "English"), ("es", "Spanish")],
                default="en",
                max_length=2,
            ),
        ),
        migrations.AddField(
            model_name="webformsubmission",
            name="confirmation_completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="webformsubmission",
            name="confirmation_claim_id",
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="webformsubmission",
            name="confirmation_claimed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
