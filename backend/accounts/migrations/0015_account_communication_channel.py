from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0014_account_appointment")]
    operations = [
        migrations.AddField(
            model_name="account",
            name="preferred_communication_channel",
            field=models.CharField(
                max_length=16,
                choices=[("SMS", "SMS"), ("CALL", "Call"), ("EMAIL", "Email")],
                blank=True,
                null=True,
            ),
        )
    ]
