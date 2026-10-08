from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("common", "0072_user_ui_language")]
    operations = [
        migrations.AddField(
            model_name="profile",
            name="setup_step",
            field=models.CharField(
                choices=[
                    ("complete", "Complete"),
                    ("profile", "Profile"),
                    ("profile_organization", "Profile and organization"),
                    ("organization", "Organization"),
                ],
                default="complete",
                editable=False,
                max_length=24,
            ),
        )
    ]
