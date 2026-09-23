from django.db import migrations


def optional_properties(apps, schema_editor):
    apps.get_model('common', 'CustomFieldDefinition').objects.filter(
        target_model__in=['Contact', 'Account', 'Opportunity', 'Task', 'Case'],
        is_required=True,
    ).update(is_required=False)


class Migration(migrations.Migration):
    dependencies = [('common', '0061_retire_contact_marketing_property')]
    operations = [migrations.RunPython(optional_properties, migrations.RunPython.noop)]
