from django.db import migrations

from common.rls import get_enable_policy_sql


def enable(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(get_enable_policy_sql("crm_role"))


class Migration(migrations.Migration):
    dependencies = [("common", "0051_crm_access_roles")]
    operations = [migrations.RunPython(enable, migrations.RunPython.noop)]
