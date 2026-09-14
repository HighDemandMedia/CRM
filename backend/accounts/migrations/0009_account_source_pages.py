from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0008_account_is_sample")]
    operations = [
        migrations.AddField(
            model_name="account",
            name="source",
            field=models.CharField(
                max_length=32,
                choices=(
                    ("META", "Meta"),
                    ("GOOGLE", "Google"),
                    ("TIKTOK", "TikTok"),
                    ("ORGANIC", "Organic"),
                    ("CALL", "Call"),
                    ("CUSTOMER_REFERAL", "Customer Referal"),
                    ("EMPLOYER_REFERAL", "Employer Referal"),
                    ("WALK_IN", "Walk In"),
                ),
                blank=True,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="account",
            name="pages",
            field=models.JSONField(default=list, blank=True),
        ),
    ]
