from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("contacts", "0017_contact_appointment_at")]
    operations = [
        migrations.AddField(
            model_name="contact",
            name="language",
            field=models.CharField("Language", max_length=100, blank=True, default=""),
        )
    ]
