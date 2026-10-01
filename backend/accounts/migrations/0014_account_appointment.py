from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0013_account_language")]
    operations = [
        migrations.AddField(
            model_name="account",
            name="appointment_at",
            field=models.DateTimeField(
                "Appointment", null=True, blank=True, db_index=True
            ),
        )
    ]
