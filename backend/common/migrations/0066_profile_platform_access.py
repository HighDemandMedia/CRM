from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("common", "0065_permission_set_audit_event")]
    operations = [
        migrations.AddField(
            model_name="profile",
            name="is_platform_access",
            field=models.BooleanField(default=False, editable=False),
        )
    ]
