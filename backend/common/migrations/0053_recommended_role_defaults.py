from django.db import migrations


def apply_defaults(apps, schema_editor):
    Role = apps.get_model('common', 'CRMRole')
    Org = apps.get_model('common', 'Org')
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        previous = None
        if connection.vendor == 'postgresql':
            cursor.execute("SELECT current_setting('app.current_org', true)")
            previous = cursor.fetchone()[0]
        try:
            for org in Org.objects.all().iterator():
                if connection.vendor == 'postgresql':
                    cursor.execute("SELECT set_config('app.current_org', %s, true)", [str(org.pk)])
                for role in Role.objects.filter(org_id=org.pk, name__in=['Member', 'Manager']):
                    rules = dict(role.rules)
                    for module, permissions in rules.items():
                        rules[module] = {**permissions, 'delete': 'none', 'export': 'none', 'reassign': 'team' if role.name == 'Manager' else 'none'}
                    role.rules = rules
                    role.save(update_fields=['rules'])
        finally:
            if connection.vendor == 'postgresql':
                cursor.execute("SELECT set_config('app.current_org', %s, true)", [previous or ''])


class Migration(migrations.Migration):
    dependencies = [('common', '0052_crm_role_rls')]
    operations = [migrations.RunPython(apply_defaults, migrations.RunPython.noop)]
