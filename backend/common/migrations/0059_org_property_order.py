from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("common", "0058_organization_pipeline_settings")]
    operations = [
        migrations.AddField(
            model_name="org",
            name="property_order",
            field=models.JSONField(default=dict, blank=True),
        )
    ]
