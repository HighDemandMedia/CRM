from django.db import migrations


def number_tickets(apps, schema_editor):
    Case = apps.get_model('cases', 'Case')
    Sequence = apps.get_model('cases', 'TicketSequence')
    Org = apps.get_model('common', 'Org')
    connection = schema_editor.connection
    previous = ''
    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.current_org', true)")
            previous = cursor.fetchone()[0] or ''
    try:
        for org_id in Org.objects.values_list('id', flat=True):
            if connection.vendor == 'postgresql':
                with connection.cursor() as cursor:
                    cursor.execute("SELECT set_config('app.current_org', %s, true)", [str(org_id)])
            Org.objects.select_for_update().get(pk=org_id)
            sequence, _ = Sequence.objects.get_or_create(org_id=org_id)
            for pk in Case.objects.filter(org_id=org_id, ticket_number__isnull=True).order_by('created_at', 'id').values_list('id', flat=True):
                sequence.last_number += 1
                Case.objects.filter(pk=pk).update(ticket_number=sequence.last_number)
            sequence.save(update_fields=['last_number'])
    finally:
        if connection.vendor == 'postgresql':
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('app.current_org', %s, true)", [previous])


class Migration(migrations.Migration):
    dependencies = [('cases', '0031_ticketsequence_case_category_case_deal_case_due_at_and_more')]
    operations = [migrations.RunPython(number_tickets, migrations.RunPython.noop)]
