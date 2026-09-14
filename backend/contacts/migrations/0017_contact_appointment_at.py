from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("contacts", "0016_contact_stage_entered_at")]
    operations = [
        migrations.AddField(
            model_name="contact",
            name="appointment_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Appointment"
            ),
        ),
    ]
