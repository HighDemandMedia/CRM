import pytest
from common.models import SalesAppointment

@pytest.mark.django_db
def test_create_read_and_scope(admin_client, admin_profile, org_b_client, org_a):
    payload = {'title':'Consultation','host':str(admin_profile.pk),'starts_at':'2026-09-13T13:00:00Z','ends_at':'2026-09-13T14:30:00Z','internal_notes':'Internal preparation'}
    response = admin_client.post('/api/sales-appointments/',payload,format='json')
    assert response.status_code == 201, response.data
    record = SalesAppointment.objects.get(pk=response.data['id'])
    assert record.org_id == org_a.pk
    assert record.created_by_id == admin_profile.user_id
    query={'start':'2026-09-13T00:00:00Z','end':'2026-09-14T00:00:00Z'}
    own = admin_client.get('/api/sales-appointments/',query)
    assert own.status_code == 200
    assert own.data[0]['internal_notes'] == payload['internal_notes']
    foreign = org_b_client.get('/api/sales-appointments/',query)
    assert foreign.data == []
    rejected = org_b_client.post('/api/sales-appointments/',payload,format='json')
    assert rejected.status_code == 400

@pytest.mark.django_db
def test_rejects_invalid_interval_and_required_fields(admin_client, admin_profile):
    payload={'title':'Meeting','host':str(admin_profile.pk),'starts_at':'2026-09-13T14:00:00Z','ends_at':'2026-09-13T13:00:00Z'}
    assert admin_client.post('/api/sales-appointments/',payload,format='json').status_code == 400
    assert admin_client.post('/api/sales-appointments/',{},format='json').status_code == 400
    assert SalesAppointment.objects.count() == 0

@pytest.mark.django_db
@pytest.mark.parametrize('kind', ['contact','company'])
def test_attendee_selection_and_scope(admin_client, admin_profile, org_a, org_b, kind):
    from contacts.models import Contact
    from accounts.models import Account
    model = Contact if kind == 'contact' else Account
    fields = {'first_name':'Attendee'} if kind == 'contact' else {'name':'Attendee'}
    local = model.objects.create(org=org_a, **fields)
    foreign = model.objects.create(org=org_b, **fields)
    payload = {'title':'Event','host':str(admin_profile.pk),'starts_at':'2026-09-13T13:00:00Z','ends_at':'2026-09-13T14:00:00Z',kind:str(local.pk),'internal_notes':'Prepare the consultation'}
    created = admin_client.post('/api/sales-appointments/',payload,format='json')
    assert created.status_code == 201, created.data
    assert created.data['attendee']['name'] == 'Attendee'
    assert created.data['attendee']['type'] == kind
    from common.models import Comment
    from django.contrib.contenttypes.models import ContentType
    notes = Comment.objects.filter(content_type=ContentType.objects.get_for_model(model),object_id=local.pk)
    note = notes.get()
    assert note.comment == 'Prepare the consultation'
    assert note.org_id == org_a.pk and note.commented_by_id == admin_profile.pk
    assert note.is_internal and note.commented_on

    local.refresh_from_db()
    assert local.appointment_at.isoformat() == '2026-09-13T13:00:00+00:00'
    from common.models import Activity
    history = Activity.objects.get(entity_id=local.pk, description='Event scheduled: Event')
    assert history.metadata['actor'] == admin_profile.user.email
    assert history.user_id == admin_profile.pk
    url=f"/api/sales-appointments/{created.data['id']}/"
    moved=admin_client.patch(url,{'operation':'reschedule','starts_at':'2026-09-14T15:00:00Z','ends_at':'2026-09-14T16:00:00Z'},format='json')
    assert moved.status_code == 200
    local.refresh_from_db()
    assert local.appointment_at.day == 14
    assert admin_client.patch(url,{'operation':'cancel'},format='json').status_code == 200
    local.refresh_from_db()
    assert local.appointment_at is None
    assert notes.count() == 1  # Rescheduling and cancelling must not duplicate notes.
    assert Activity.objects.filter(entity_id=local.pk,description='Event cancelled: Event').exists()
    payload[kind] = str(foreign.pk)
    assert admin_client.post('/api/sales-appointments/',payload,format='json').status_code == 400
    choices = admin_client.get('/api/sales-appointments/attendees/', {'search':'Attendee'})
    key = 'contacts' if kind == 'contact' else 'companies'
    assert [entry['id'] for entry in choices.data[key]] == [str(local.pk)]

@pytest.mark.django_db
def test_reschedule_cancel_and_history(admin_client, admin_profile, org_b_client):
    data={'title':'Manage test','host':str(admin_profile.pk),'starts_at':'2026-09-13T13:00:00Z','ends_at':'2026-09-13T14:00:00Z'}
    created=admin_client.post('/api/sales-appointments/',data,format='json')
    url=f"/api/sales-appointments/{created.data['id']}/"
    change={'operation':'reschedule','starts_at':'2026-09-14T15:00:00Z','ends_at':'2026-09-14T16:00:00Z'}
    assert org_b_client.patch(url,change,format='json').status_code == 404
    assert admin_client.patch(url,{**change,'ends_at':change['starts_at']},format='json').status_code == 400
    assert admin_client.patch(url,change,format='json').status_code == 200
    record=SalesAppointment.objects.get(pk=created.data['id'])
    assert record.starts_at.day == 14
    assert record.change_history[0]['action']=='reschedule'
    assert record.change_history[0]['by']==str(admin_profile.user_id)
    assert admin_client.patch(url,{'operation':'cancel'},format='json').status_code == 200
    record.refresh_from_db()
    assert record.cancelled_at is not None
    assert record.cancelled_by_id == admin_profile.user_id
    assert len(record.change_history)==2
    # A repeated cancel must not produce extra history or restore the event.
    assert admin_client.patch(url,{'operation':'cancel'},format='json').status_code == 200
    record.refresh_from_db()
    assert len(record.change_history)==2
    assert admin_client.patch(url,change,format='json').status_code == 409
    visible=admin_client.get('/api/sales-appointments/',{'start':'2026-09-13T00:00:00Z','end':'2026-09-16T00:00:00Z'})
    assert visible.data == []

@pytest.mark.django_db
def test_host_overlap_boundaries_cancel_and_reschedule(admin_client, admin_profile, user_profile):
    endpoint = '/api/sales-appointments/'
    def book(start, end, host=admin_profile):
        return admin_client.post(endpoint, {
            'title': 'Availability test', 'host': str(host.pk),
            'starts_at': f'2026-09-15T{start}:00Z',
            'ends_at': f'2026-09-15T{end}:00Z',
        }, format='json')
    first = book('13:00', '14:00')
    assert first.status_code == 201
    for start, end in [('13:00','14:00'), ('12:30','13:30'), ('13:30','14:30'), ('12:00','15:00'), ('13:15','13:45')]:
        assert book(start,end).status_code == 400
    assert book('13:00','14:00',user_profile).status_code == 201
    assert book('12:00','13:00').status_code == 201
    second = book('14:00','15:00')
    assert second.status_code == 201
    url = f"{endpoint}{second.data['id']}/"
    change = {'operation':'reschedule','starts_at':'2026-09-15T13:30:00Z','ends_at':'2026-09-15T14:30:00Z'}
    assert admin_client.patch(url,change,format='json').status_code == 400
    record = SalesAppointment.objects.get(pk=second.data['id'])
    assert record.starts_at.hour == 14 and record.change_history == []
    change.update(starts_at='2026-09-15T14:00:00Z',ends_at='2026-09-15T15:00:00Z')
    assert admin_client.patch(url,change,format='json').status_code == 200
    assert admin_client.patch(f"{endpoint}{first.data['id']}/",{'operation':'cancel'},format='json').status_code == 200
    assert book('13:00','14:00').status_code == 201

@pytest.mark.django_db
def test_availability_scope_exclusion_and_privacy(admin_client, admin_profile, org_b_client, user_client):
    created = admin_client.post('/api/sales-appointments/',{
        'title':'Private title','internal_notes':'Private notes','host':str(admin_profile.pk),
        'starts_at':'2026-09-15T13:00:00Z','ends_at':'2026-09-15T14:00:00Z',
    },format='json')
    query = {'host':str(admin_profile.pk),'start':'2026-09-15T00:00:00Z','end':'2026-09-16T00:00:00Z'}
    endpoint = '/api/sales-appointments/availability/'
    response = admin_client.get(endpoint,query)
    assert response.status_code == 200
    assert admin_client.get(endpoint,{**query,'end':'2026-09-22T00:00:00Z'}).status_code == 200
    assert admin_client.get(endpoint,{**query,'end':'2026-09-25T00:00:00Z'}).status_code == 400
    assert len(response.data['busy']) == 1
    assert set(response.data['busy'][0]) == {'starts_at','ends_at','title'}
    assert response.data['busy'][0]['title'] == 'Private title'
    assert user_client.get(endpoint,query).data['busy'][0]['title'] is None
    assert org_b_client.get(endpoint,query).status_code == 404
    assert admin_client.get(endpoint,{**query,'exclude':created.data['id']}).data == {'busy':[]}
    assert admin_client.get(endpoint,{**query,'start':query['end']}).status_code == 400
    assert admin_client.patch(f"/api/sales-appointments/{created.data['id']}/",{'operation':'cancel'},format='json').status_code == 200
    assert admin_client.get(endpoint,query).data == {'busy':[]}

@pytest.mark.django_db
def test_overlap_requires_explicit_confirmation(admin_client, admin_profile):
    endpoint = '/api/sales-appointments/'
    payload = {'title':'Confirmed overlap','host':str(admin_profile.pk),
               'starts_at':'2026-09-15T13:00:00Z','ends_at':'2026-09-15T14:00:00Z'}
    assert admin_client.post(endpoint,payload,format='json').status_code == 201
    for value in [False, 'false']:
        assert admin_client.post(endpoint,{**payload,'allow_overlap':value},format='json').status_code == 400
    assert admin_client.post(endpoint,{**payload,'allow_overlap':'invalid'},format='json').status_code == 400
    assert SalesAppointment.objects.count() == 1
    assert admin_client.post(endpoint,{**payload,'allow_overlap':True},format='json').status_code == 201
    assert SalesAppointment.objects.count() == 2
    # Confirmation applies only to that request, not subsequent bookings.
    assert admin_client.post(endpoint,payload,format='json').status_code == 400

@pytest.mark.django_db
@pytest.mark.parametrize('kind',['contact','company'])
def test_event_creates_associated_deal(admin_client, admin_profile, org_a, kind):
    from contacts.models import Contact
    from accounts.models import Account
    from opportunity.models import Opportunity
    from common.models import Comment
    model = Contact if kind == 'contact' else Account
    fields = {'first_name':'Attendee'} if kind == 'contact' else {'name':'Attendee'}
    attendee = model.objects.create(org=org_a, source='META', language='Spanish', phone='3055550188', email='attendee@example.com',city='Miami',**fields)
    body={'title':'Event','host':str(admin_profile.pk),'starts_at':'2026-09-15T13:00:00Z','ends_at':'2026-09-15T14:00:00Z','create_deal':True,kind:str(attendee.pk),'internal_notes':'Only attendee notes'}
    response=admin_client.post('/api/sales-appointments/',body,format='json')
    assert response.status_code == 201, response.data
    appointment=SalesAppointment.objects.get(pk=response.data['id'])
    deal=appointment.deal
    assert deal.name=='Attendee - Deal' and deal.lead_source=='META'
    assert deal.priority=='MEDIUM' and deal.stage=='PROSPECTING'
    assert deal.phone==attendee.phone and deal.email==attendee.email and deal.city=='Miami'
    assert deal.language=='Spanish' and deal.assigned_to.filter(pk=admin_profile.pk).exists()
    assert deal.org_id==org_a.pk and deal.created_by_id==admin_profile.user_id
    assert deal.amount is None and deal.closed_on is None and not deal.description and not deal.tags.exists()
    assert not Comment.objects.filter(object_id=deal.pk).exists()
    if kind=='contact': assert deal.contacts.filter(pk=attendee.pk).exists()
    else: assert deal.account_id==attendee.pk
    admin_client.patch(f'/api/sales-appointments/{appointment.pk}/',{'operation':'cancel'},format='json')
    assert Opportunity.objects.filter(pk=deal.pk).exists()

@pytest.mark.django_db
def test_event_deal_missing_source_is_atomic_and_optional(admin_client,admin_profile,org_a):
    from contacts.models import Contact
    from opportunity.models import Opportunity
    attendee=Contact.objects.create(first_name='No source',org=org_a)
    body={'title':'Event','host':str(admin_profile.pk),'starts_at':'2026-09-15T13:00:00Z','ends_at':'2026-09-15T14:00:00Z','create_deal':True,'contact':str(attendee.pk)}
    assert admin_client.post('/api/sales-appointments/',body,format='json').status_code==400
    assert not SalesAppointment.objects.exists() and not Opportunity.objects.exists()
    response=admin_client.post('/api/sales-appointments/',{**body,'deal_source':'GOOGLE','deal_name':'Custom deal'},format='json')
    assert response.status_code==201,response.data
    assert Opportunity.objects.get().name=='Custom deal'
    response=admin_client.post('/api/sales-appointments/',{**body,'create_deal':False,'starts_at':'2026-09-16T13:00:00Z','ends_at':'2026-09-16T14:00:00Z'},format='json')
    assert response.status_code==201 and response.data['deal'] is None
    assert Opportunity.objects.count()==1
