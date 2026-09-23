import pytest
from rest_framework.exceptions import ValidationError
from common.pipeline_settings import stages_for, validate_entry
from contacts.models import Contact
from opportunity.models import Opportunity

URL = '/api/pipeline-settings/'


def configure(client, target, mutate):
    current = client.get(URL).json()
    stages = current['pipelines'][target]['stages']
    mutate(stages)
    return client.put(URL, {'target_model': target, 'revision': current['revision'], 'stages': stages}, format='json')


@pytest.mark.django_db
def test_configuration_is_scoped_and_internal_names_fixed(admin_client, org_a, org_b):
    def change(stages):
        stages.reverse()
        stages[0]['label'] = 'Custom label'
    assert configure(admin_client, 'Contact', change).status_code == 200
    org_a.refresh_from_db()
    assert stages_for(org_a, 'Contact')[0]['label'] == 'Custom label'
    assert stages_for(org_b, 'Contact')[0]['key'] == 'LEAD'
    assert configure(admin_client, 'Contact', lambda rows: rows[0].update(key='NEW_KEY')).status_code == 400


@pytest.mark.django_db
def test_admin_only_and_stale_save(admin_client, user_client):
    assert user_client.get(URL).status_code == 200
    assert user_client.put(URL, {}, format='json').status_code == 403
    assert admin_client.put(URL, {'target_model': 'Contact', 'revision': 'stale', 'stages': []}, format='json').status_code == 409


@pytest.mark.django_db
@pytest.mark.parametrize('bad', [None, [{'key': []}], 'bad'])
def test_malformed_stages(admin_client, bad):
    revision = admin_client.get(URL).json()['revision']
    assert admin_client.put(URL, {'target_model': 'Contact', 'revision': revision, 'stages': bad}, format='json').status_code == 400


@pytest.mark.django_db
def test_entry_rules_only_apply_on_entry(admin_client, org_a):
    def change(rows):
        next(s for s in rows if s['key'] == 'QUALIFIED').update(required_fields=['email'], allowed_from=['FOLLOW_UP'])
    assert configure(admin_client, 'Contact', change).status_code == 200
    org_a.refresh_from_db()
    record = Contact.objects.create(org=org_a, first_name='Rules', stage='LEAD')
    with pytest.raises(ValidationError, match='current stage'):
        validate_entry(org_a, 'Contact', record, {'stage': 'QUALIFIED', 'email': 'ok@example.com'})
    record.stage = 'FOLLOW_UP'
    with pytest.raises(ValidationError, match='Email'):
        validate_entry(org_a, 'Contact', record, {'stage': 'QUALIFIED'})
    validate_entry(org_a, 'Contact', record, {'stage': 'QUALIFIED', 'email': 'ok@example.com'})
    record.stage = 'QUALIFIED'
    validate_entry(org_a, 'Contact', record, {'first_name': 'Unrelated edit'})


@pytest.mark.django_db
def test_default_create_and_false_values(admin_client, org_a):
    assert configure(admin_client, 'Account', lambda rows: rows[0].update(required_fields=['email'])).status_code == 200
    org_a.refresh_from_db()
    with pytest.raises(ValidationError, match='Email'):
        validate_entry(org_a, 'Account', None, {'first_name': 'Missing'})
    validate_entry(org_a, 'Account', None, {'first_name': 'Ready', 'email': 'ok@example.com'})


@pytest.mark.django_db
def test_deal_probability_updates_existing_and_new(admin_client, org_a):
    existing = Opportunity.objects.create(org=org_a, name='Forecast', stage='PROSPECTING', amount=1000)
    assert configure(admin_client, 'Opportunity', lambda rows: next(s for s in rows if s['key']=='PROSPECTING').update(percentage=35)).status_code == 200
    existing.refresh_from_db()
    assert existing.probability == 35
    org_a.refresh_from_db()
    new = Opportunity.objects.create(org=org_a, name='New forecast', stage='PROSPECTING')
    assert new.probability == 35
    assert configure(admin_client, 'Opportunity', lambda rows: next(s for s in rows if s['key']=='CLOSED_WON').update(percentage=90)).status_code == 200


@pytest.mark.django_db
def test_contact_patch_enforces_rules(admin_client, org_a):
    assert configure(admin_client, 'Contact', lambda rows: next(s for s in rows if s['key']=='QUALIFIED').update(required_fields=['email'])).status_code == 200
    record = Contact.objects.create(org=org_a, first_name='Endpoint rules', stage='FOLLOW_UP')
    response = admin_client.patch(f'/api/contacts/{record.pk}/', {'stage':'QUALIFIED'}, format='json')
    assert response.status_code == 400, response.data
    record.refresh_from_db()
    assert record.stage == 'FOLLOW_UP'

@pytest.mark.django_db
@pytest.mark.parametrize('target,field,destination,property_key', [('Account','stage','QUALIFIED','email'), ('Opportunity','stage','PROPOSAL','email'), ('Task','status','In Progress','due_date'), ('Case','status','Pending','waiting_reason')])
def test_other_object_rules(admin_client, org_a, target, field, destination, property_key):
    from common.property_catalog import target_model
    assert configure(admin_client, target, lambda rows: next(s for s in rows if s['key']==destination).update(required_fields=[property_key])).status_code == 200
    org_a.refresh_from_db()
    record = target_model(target)(org=org_a)
    with pytest.raises(ValidationError):
        validate_entry(org_a, target, record, {field: destination})


@pytest.mark.django_db
def test_custom_false_and_zero_are_values(admin_client, org_a):
    from common.models import CustomFieldDefinition
    for key, kind in [('accepted','checkbox'), ('score','number')]:
        CustomFieldDefinition.objects.create(org=org_a, target_model='Contact', key=key, label=key, field_type=kind)
    assert configure(admin_client, 'Contact', lambda rows: next(s for s in rows if s['key']=='QUALIFIED').update(required_fields=['custom_fields.accepted','custom_fields.score'])).status_code == 200
    org_a.refresh_from_db()
    record = Contact(org=org_a, stage='FOLLOW_UP', custom_fields={'accepted':False, 'score':0})
    validate_entry(org_a, 'Contact', record, {'stage':'QUALIFIED'})
    with pytest.raises(ValidationError):
        validate_entry(org_a, 'Contact', record, {'stage':'QUALIFIED'}, {'custom_fields': {'score':None}})


@pytest.mark.django_db
def test_task_move_cannot_bypass_rules(admin_client, org_a):
    from tasks.models import Task
    assert configure(admin_client, 'Task', lambda rows: next(s for s in rows if s['key']=='In Progress').update(required_fields=['due_date'])).status_code == 200
    task = Task.objects.create(org=org_a, title='Gate', status='New', priority='Low')
    response = admin_client.patch(f'/api/tasks/{task.pk}/move/', {'status':'In Progress'}, format='json')
    assert response.status_code == 400, response.data
    task.refresh_from_db()
    assert task.status == 'New'


@pytest.mark.django_db
@pytest.mark.parametrize('query', ['', '?include_pipeline_totals=true&limit=1', '?stage=LEAD&include_deal_values=true'])
def test_contacts_list_loads_configured_stages(admin_client, org_a, query):
    def change(rows):
        rows.reverse()
        next(s for s in rows if s['key'] == 'LEAD')['label'] = 'New inquiry'
    assert configure(admin_client, 'Contact', change).status_code == 200
    Contact.objects.create(org=org_a, first_name='List regression', stage='LEAD')
    response = admin_client.get('/api/contacts/' + query)
    assert response.status_code == 200, response.data
    assert response.data['stages'][0][0] == 'LOST'
    assert dict(response.data['stages'])['LEAD'] == 'New inquiry'

@pytest.mark.django_db
@pytest.mark.parametrize('target,endpoint,field,destination,required,missing_value', [
    ('Contact','contacts','stage','QUALIFIED','email','completion@example.com'),
    ('Account','accounts','stage','QUALIFIED','email','company-completion@example.com'),
    ('Opportunity','opportunities','stage','PROPOSAL','email','deal-completion@example.com'),
    ('Task','tasks','status','In Progress','description','Preparation complete'),
    ('Case','cases','status','Assigned','description','Ticket details')])
def test_complete_requirements_and_move_atomically(admin_client, org_a, target, endpoint, field, destination, required, missing_value):
    from common.property_catalog import target_model
    model=target_model(target)
    kwargs={'org':org_a, field:'New' if field=='status' else 'LEAD' if target!='Opportunity' else 'PROSPECTING'}
    kwargs['title' if target=='Task' else 'first_name' if target=='Contact' else 'name']='Transition test'
    if target=='Task': kwargs['priority']='Low'
    if target=='Case': kwargs['priority']='Normal'
    record=model.objects.create(**kwargs)
    assert configure(admin_client,target,lambda rows:next(s for s in rows if s['key']==destination).update(required_fields=[required])).status_code==200
    response=admin_client.patch(f'/api/{endpoint}/{record.pk}/',{field:destination},format='json')
    assert response.status_code==400,response.data
    issue=response.data.get('errors',response.data)['stage_requirements']
    assert issue['code']=='missing_properties'
    assert issue['fields'][0]['key']==required
    record.refresh_from_db()
    assert getattr(record,field)==kwargs[field]
    response=admin_client.patch(f'/api/{endpoint}/{record.pk}/',{field:destination,required:missing_value},format='json')
    assert response.status_code==200,response.data
    record.refresh_from_db()
    assert getattr(record,field)==destination
    assert getattr(record,required)==missing_value


def save_stages(client, target, mutate, additions=None, removals=None):
    current = client.get(URL).json()
    rows = current['pipelines'][target]['stages']
    mutate(rows)
    return client.put(URL, {'target_model': target, 'revision': current['revision'], 'stages': rows, 'additions': additions or [], 'removals': removals or {}}, format='json')


@pytest.mark.django_db
@pytest.mark.parametrize('target,endpoint,field', [('Contact','contacts','stage'), ('Account','accounts','stage'), ('Opportunity','opportunities','stage'), ('Task','tasks','status'), ('Case','cases','status')])
def test_custom_stages_move_and_remove(admin_client, org_a, org_b, target, endpoint, field):
    from common.property_catalog import target_model
    key = 'custom_test_stage'
    response = save_stages(admin_client, target, lambda rows: rows.append({'key': key, 'label': 'Review queue', 'percentage': 20}), [key])
    assert response.status_code == 200, response.data
    org_a.refresh_from_db()
    assert key in {s['key'] for s in stages_for(org_a, target)}
    assert key not in {s['key'] for s in stages_for(org_b, target)}
    initial = stages_for(org_a, target)[0]['key']
    kwargs = {'org': org_a, field: initial, 'title' if target=='Task' else 'first_name' if target=='Contact' else 'name': 'Custom stage test'}
    if target in ('Task','Case'): kwargs['priority'] = 'Low' if target=='Task' else 'Normal'
    record = target_model(target).objects.create(**kwargs)
    response = admin_client.patch(f'/api/{endpoint}/{record.pk}/', {field:key}, format='json')
    assert response.status_code == 200, response.data
    record.refresh_from_db()
    assert getattr(record, field) == key
    # Move endpoints and kanban support custom keys too.
    if target in ('Task', 'Opportunity', 'Case'):
        response = admin_client.patch(f'/api/{endpoint}/{record.pk}/move/', {'column_id' if target=='Opportunity' else field:key}, format='json')
        assert response.status_code == 200, response.data
        response = admin_client.get(f'/api/{endpoint}/kanban/')
        assert response.status_code == 200, response.data
        assert key in {str(s['id']) for s in response.data['columns']}
    response = save_stages(admin_client, target, lambda rows: rows.__setitem__(slice(None), [s for s in rows if s['key']!=key]), removals={key:None})
    assert response.status_code == 400, response.data
    response = save_stages(admin_client, target, lambda rows: rows.__setitem__(slice(None), [s for s in rows if s['key']!=key]), removals={key:initial})
    assert response.status_code == 200, response.data
    record.refresh_from_db()
    assert getattr(record, field) == initial
    assert admin_client.patch(f'/api/{endpoint}/{record.pk}/', {field:key}, format='json').status_code == 400


@pytest.mark.django_db
def test_removing_stage_with_unmet_rules_rolls_back(admin_client, org_a):
    assert configure(admin_client, 'Contact', lambda rows: next(s for s in rows if s['key']=='QUALIFIED').update(required_fields=['email'])).status_code == 200
    assert save_stages(admin_client, 'Contact', lambda rows: rows.append({'key':'custom_review','label':'Review queue','percentage':25}), ['custom_review']).status_code == 200
    a = Contact.objects.create(org=org_a, first_name='Ready', stage='custom_review', email='ready@example.com')
    b = Contact.objects.create(org=org_a, first_name='Missing email', stage='custom_review')
    response = save_stages(admin_client, 'Contact', lambda rows: rows.__setitem__(slice(None), [s for s in rows if s['key']!='custom_review']), removals={'custom_review':'QUALIFIED'})
    assert response.status_code == 400, response.data
    a.refresh_from_db(); b.refresh_from_db(); org_a.refresh_from_db()
    assert a.stage == b.stage == 'custom_review'
    assert 'custom_review' in {s['key'] for s in stages_for(org_a, 'Contact')}


@pytest.mark.django_db
@pytest.mark.parametrize('target', ['Contact','Account','Opportunity','Task','Case'])
def test_default_stages_protected_and_all_percentages_editable(admin_client, org_a, target):
    original = admin_client.get(URL).json()['pipelines'][target]['stages']
    assert all(stage['protected'] for stage in original)
    for stage in original:
        key = stage['key']
        response = save_stages(admin_client, target, lambda rows: rows.__setitem__(slice(None), [s for s in rows if s['key'] != key]), removals={key:None})
        assert response.status_code == 400, response.data
    assert configure(admin_client, target, lambda rows: [s.update(percentage=37) for s in rows]).status_code == 200
    result = admin_client.get(URL).json()['pipelines'][target]['stages']
    assert all(s['percentage'] == 37 and not s['locked_percentage'] for s in result)
    assert save_stages(admin_client, target, lambda rows: rows.append({'key':'custom_temporary','label':'Temporary','percentage':15}), ['custom_temporary']).status_code == 200
    response = save_stages(admin_client, target, lambda rows: rows.__setitem__(slice(None), [s for s in rows if s['key'] != 'custom_temporary']), removals={'custom_temporary':None})
    assert response.status_code == 200, response.data


@pytest.mark.django_db
def test_custom_open_stages_in_company_and_today_totals(admin_client, org_a, admin_user):
    from accounts.models import Account
    from tasks.models import Task
    from cases.models import Case
    from django.utils import timezone
    key = 'custom_review'
    for target in ('Task', 'Case', 'Opportunity'):
        assert save_stages(admin_client, target, lambda rows: rows.append({'key':key,'label':'Review queue','percentage':30}), [key]).status_code == 200
    org_a.refresh_from_db()
    company = Account.objects.create(org=org_a,name='Totals',website='totals.example')
    Opportunity.objects.create(org=org_a,created_by=admin_user,account=company,name='Review deal',stage=key,amount=500,closed_on=timezone.localdate())
    Task.objects.create(org=org_a,created_by=admin_user,title='Review task',status=key,priority='Low',due_date=timezone.localdate())
    Case.objects.create(org=org_a,created_by=admin_user,account=company,name='Review ticket',status=key,priority='Normal',due_at=timezone.now())
    response = admin_client.get('/api/dashboard/day-summary/')
    assert response.status_code == 200, response.data
    assert response.data['counts']['tasks'] == response.data['counts']['tickets'] == response.data['counts']['deals'] == 1
    from accounts.views import annotate_rollups
    company = annotate_rollups(Account.objects.filter(pk=company.pk)).get()
    assert company.open_deal_count == company.open_tickets == 1
    assert company.open_pipeline == 500
