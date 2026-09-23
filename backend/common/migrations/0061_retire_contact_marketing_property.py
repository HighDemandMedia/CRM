from django.db import migrations


def retire_property(apps, schema_editor):
    Org = apps.get_model('common', 'Org')
    for org in Org.objects.all().iterator():
        changed = []
        order = (org.property_order or {}).get('Contact', [])
        if 'do_not_call' in order:
            org.property_order['Contact'] = [key for key in order if key != 'do_not_call']
            changed.append('property_order')
        for stage in (org.pipeline_settings or {}).get('Contact', []):
            if 'do_not_call' in stage.get('required_fields', []):
                stage['required_fields'] = [key for key in stage['required_fields'] if key != 'do_not_call']
                if 'pipeline_settings' not in changed:
                    changed.append('pipeline_settings')
        if changed:
            org.save(update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [('common', '0060_profile_demo_view')]
    operations = [migrations.RunPython(retire_property, migrations.RunPython.noop)]
