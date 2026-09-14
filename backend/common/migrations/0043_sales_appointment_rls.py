from django.db import migrations
from common.rls import get_enable_policy_sql


def enable(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute(get_enable_policy_sql('sales_appointment'))

class Migration(migrations.Migration):
    dependencies = [('common','0042_sales_appointment')]
    operations = [migrations.RunPython(enable, migrations.RunPython.noop)]
