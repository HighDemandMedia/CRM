from django.db import migrations, models

import common.usage_limits


class Migration(migrations.Migration):
    dependencies = [("common", "0081_org_usage_limits")]

    # Only changes the application default; no existing organization is updated.
    operations = [
        migrations.AlterField(
            model_name="org",
            name="usage_limits",
            field=models.JSONField(
                default=common.usage_limits.default_organization_limits,
                blank=True,
                editable=False,
            ),
        ),
    ]
