from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("common", "0071_invitation_grants_ownership")]
    operations = [
        migrations.AddField(
            model_name="user",
            name="ui_language",
            field=models.CharField(
                choices=[("en", "English"), ("es", "Español")],
                default="en",
                max_length=2,
            ),
        )
    ]
