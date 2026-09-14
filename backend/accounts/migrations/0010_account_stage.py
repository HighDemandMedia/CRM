import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0009_account_source_pages")]
    operations = [
        migrations.AddField(
            model_name="account",
            name="stage",
            field=models.CharField(
                max_length=32,
                choices=(
                    ("LEAD", "Lead"),
                    ("FOLLOW_UP", "Follow Up"),
                    ("QUALIFIED", "Qualified"),
                    ("NOT_QUALIFIED", "Not Qualified"),
                    ("LOST", "Lost"),
                ),
                default="LEAD",
            ),
        ),
        migrations.AddField(
            model_name="account",
            name="stage_entered_at",
            field=models.DateTimeField(
                default=django.utils.timezone.now, editable=False
            ),
        ),
    ]
