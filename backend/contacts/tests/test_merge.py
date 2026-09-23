import pytest
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from accounts.models import Account
from contacts.models import Contact
from common.models import Activity, Comment, Tags, SalesAppointment, PortalLoginToken
from opportunity.models import Opportunity
from tasks.models import Task
from cases.models import Case

pytestmark = pytest.mark.django_db


def pair(org):
    return (Contact.objects.create(org=org, first_name='Primary', email='primary@example.com'),
            Contact.objects.create(org=org, first_name='Secondary', email='secondary@example.com', phone='+13055550199'))


def preview(client, primary, secondary):
    response = client.get(f'/api/contacts/{primary.pk}/merge/', {'secondary':str(secondary.pk)})
    assert response.status_code == 200, response.data
    return response.data


def merge(client, primary, plan, **kwargs):
    return client.post(f'/api/contacts/{primary.pk}/merge/', {'token':plan['token'], 'confirm':True, **kwargs}, format='json')


def test_merge_preserves_id_creation_values_and_archives_secondary(admin_client, org_a):
    a,b = pair(org_a)
    created = a.created_at
    plan = preview(admin_client,a,b)
    response = merge(admin_client,a,plan,choices={'email':'secondary', 'name':'primary'})
    assert response.status_code == 200, response.data
    a.refresh_from_db(); b = Contact.all_objects.get(pk=b.pk)
    assert a.email == 'secondary@example.com' and a.phone == b.phone
    assert a.created_at == created and response.data['id'] == str(a.pk)
    assert b.merged_into_id == a.pk and b.merged_at and not b.is_active
    assert b.merge_snapshot['primary']['email'] == 'primary@example.com'
    assert not Contact.objects.filter(pk=b.pk).exists()
    assert Contact.objects.filter(org=org_a).count() == 1
    response = admin_client.get(f'/api/contacts/{b.pk}/')
    assert response.status_code == 200, response.data
    assert response.data['contact_obj']['id'] == str(a.pk)
    assert admin_client.patch(f'/api/contacts/{b.pk}/', {'name':'Forbidden'}, format='json').status_code == 404
    assert merge(admin_client,a,plan).status_code == 200
    assert Activity.objects.filter(entity_id=a.pk, metadata__merge__source_id=str(b.pk)).count() == 1


def test_links_notes_and_history_are_combined_without_duplicates(admin_client, admin_profile, org_a):
    a,b = pair(org_a)
    company = Account.objects.create(org=org_a,name='Company')
    company.contacts.add(a,b)
    b.account=company; b.description='Original notes'; b.save()
    deal = Opportunity.objects.create(org=org_a,name='Deal'); deal.contacts.add(b)
    task = Task.objects.create(org=org_a,title='Task'); task.contacts.add(b)
    ticket = Case.objects.create(org=org_a,name='Ticket'); ticket.contacts.add(a,b)
    tag = Tags.objects.create(org=org_a,name='VIP'); b.tags.add(tag)
    b.assigned_to.add(admin_profile)
    ct = ContentType.objects.get_for_model(Contact)
    note = Comment.objects.create(org=org_a, content_type=ct,object_id=b.pk,comment='Keep author',commented_by=admin_profile)
    activity = Activity.objects.create(org=org_a,entity_type='Contact',entity_id=b.pk,entity_name=b.name,
                                     action='UPDATE',description='Earlier update',user=admin_profile)
    original_time=activity.created_at
    response = merge(admin_client,a,preview(admin_client,a,b))
    assert response.status_code == 200, response.data
    for obj in [company,deal,task,ticket]: assert list(obj.contacts.values_list('pk',flat=True)) == [a.pk]
    note.refresh_from_db(); activity.refresh_from_db(); a.refresh_from_db()
    assert note.object_id == a.pk and note.commented_by_id == admin_profile.pk
    assert activity.entity_id == a.pk and activity.created_at == original_time and activity.entity_name == b.name
    assert a.tags.filter(pk=tag.pk).exists() and a.assigned_to.filter(pk=admin_profile.pk).exists()
    assert Comment.objects.filter(object_id=a.pk, comment='Original notes').exists()


def test_merge_requires_admin_and_same_org(admin_client,user_client,org_a,org_b):
    a,b = pair(org_a)
    other = Contact.objects.create(org=org_b,first_name='Private')
    assert user_client.get(f'/api/contacts/{a.pk}/merge/', {'q':'Secondary'}).status_code == 403
    plan = preview(admin_client,a,b)
    assert merge(user_client,a,plan).status_code == 403
    assert admin_client.get(f'/api/contacts/{a.pk}/merge/', {'secondary':str(other.pk)}).status_code == 404
    assert admin_client.get(f'/api/contacts/{a.pk}/merge/', {'secondary':str(a.pk)}).status_code == 400
    assert admin_client.get(f'/api/contacts/{a.pk}/merge/', {'secondary':'invalid'}).status_code == 400


def test_stale_preview_and_unconfirmed_requests_do_not_write(admin_client,org_a):
    a,b = pair(org_a)
    plan=preview(admin_client,a,b)
    assert merge(admin_client,a,plan,confirm=False).status_code == 400
    b.phone='+13055550000'; b.save()
    assert merge(admin_client,a,plan).status_code == 400
    assert Contact.objects.filter(pk=b.pk).exists()
    assert merge(admin_client,a,preview(admin_client,a,b),choices={'id':'secondary'}).status_code == 400
    assert merge(admin_client,a,{'token':'tampered'}).status_code == 400


def test_stage_entry_rules_roll_back_entire_merge(admin_client,org_a):
    from common.tests.test_pipeline_settings import configure
    a,b=pair(org_a)
    b.stage='QUALIFIED'; b.save()
    assert configure(admin_client,'Contact', lambda rows:next(r for r in rows if r['key']=='QUALIFIED').update(required_fields=['city'])).status_code == 200
    response=merge(admin_client,a,preview(admin_client,a,b),choices={'stage':'secondary'})
    assert response.status_code == 400, response.data
    assert 'stage_requirements' in response.data
    a.refresh_from_db(); b.refresh_from_db()
    assert a.stage == 'LEAD' and b.merged_at is None


def test_search_and_chained_old_links(admin_client,org_a):
    a,b=pair(org_a)
    results=admin_client.get(f'/api/contacts/{a.pk}/merge/',{'q':'secondary@example'}).data['results']
    assert [r['id'] for r in results] == [str(b.pk)]
    assert merge(admin_client,a,preview(admin_client,a,b)).status_code == 200
    c=Contact.objects.create(org=org_a,first_name='Final')
    assert merge(admin_client,c,preview(admin_client,c,a)).status_code == 200
    assert admin_client.get(f'/api/contacts/{b.pk}/').data['contact_obj']['id'] == str(c.pk)


def test_deleting_primary_does_not_reactivate_archived_contact(admin_client,org_a):
    a,b=pair(org_a)
    assert merge(admin_client,a,preview(admin_client,a,b)).status_code == 200
    a.delete()
    assert not Contact.objects.filter(pk=b.pk).exists()
    assert admin_client.get(f'/api/contacts/{b.pk}/').status_code == 404


def test_calendar_files_invoice_and_portal_identity_are_preserved_safely(admin_client,admin_profile,admin_user,org_a):
    from datetime import timedelta
    from common.models import Attachments
    from invoices.models import Invoice
    a,b=pair(org_a)
    start=timezone.now()+timedelta(days=1)
    event=SalesAppointment.objects.create(org=org_a,title='Meeting',host=admin_profile,created_by=admin_user,
        contact=b, starts_at=start,ends_at=start+timedelta(minutes=30))
    event.contacts.add(a,b)
    company=Account.objects.create(org=org_a,name='Client')
    invoice=Invoice.objects.create(org=org_a,account=company,contact=b,invoice_title='Existing invoice',currency='USD')
    ct=ContentType.objects.get_for_model(Contact)
    file=Attachments.objects.create(org=org_a,content_type=ct,object_id=b.pk,file_name='agreement.pdf',attachment='existing/agreement.pdf')
    portal_note=Comment.objects.create(org=org_a,content_type=ct,object_id=b.pk,comment='Customer reply',commented_by_contact=b)
    token=PortalLoginToken.objects.create(org=org_a,contact=b,code_hash='test',expires_at=start)
    response=merge(admin_client,a,preview(admin_client,a,b))
    assert response.status_code == 200, response.data
    event.refresh_from_db(); invoice.refresh_from_db(); file.refresh_from_db(); token.refresh_from_db(); portal_note.refresh_from_db()
    assert event.contact_id == a.pk and list(event.contacts.values_list('pk',flat=True)) == [a.pk]
    assert event.starts_at == start and event.title == 'Meeting'
    assert invoice.contact_id == a.pk and invoice.invoice_title == 'Existing invoice'
    assert file.object_id == a.pk and file.attachment.name == 'existing/agreement.pdf'
    assert portal_note.object_id == a.pk and portal_note.commented_by_contact_id == b.pk
    assert token.is_used and not Contact.objects.filter(id=b.pk,is_active=True).exists()


def test_custom_conflicts_and_member_access_to_old_link(admin_client,user_client,user_profile,org_a):
    from common.models import CustomFieldDefinition
    a,b=pair(org_a)
    CustomFieldDefinition.objects.create(org=org_a,target_model='Contact',key='reference',label='Reference',field_type='text')
    a.custom_fields={'reference':'Primary ref'}; a.save()
    b.custom_fields={'reference':'Secondary ref'}; b.save()
    b.assigned_to.add(user_profile)
    plan=preview(admin_client,a,b)
    assert any(r['key']=='custom_fields.reference' for r in plan['properties'])
    response=merge(admin_client,a,plan,choices={'custom_fields.reference':'secondary'})
    assert response.status_code == 200, response.data
    a.refresh_from_db()
    assert a.custom_fields['reference'] == 'Secondary ref'
    response=user_client.get(f'/api/contacts/{b.pk}/')
    assert response.status_code == 200, response.data
    assert response.data['contact_obj']['id'] == str(a.pk)
