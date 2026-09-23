from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('common', '0059_org_property_order')]
    operations = [migrations.AddField(model_name='profile', name='is_demo', field=models.BooleanField(default=False, editable=False))]
