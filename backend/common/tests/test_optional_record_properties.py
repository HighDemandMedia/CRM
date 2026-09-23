import pytest
from common.models import CustomFieldDefinition
from common.property_catalog import target_model
from common.tests.test_pipeline_settings import configure

pytestmark = pytest.mark.django_db
OBJECTS = [('Contact', 'contacts', 'first_name', 'stage', 'LEAD'),
           ('Account', 'accounts', 'name', 'stage', 'LEAD'),
           ('Opportunity', 'opportunities', 'name', 'stage', 'PROSPECTING'),
           ('Task', 'tasks', 'title', 'status', 'New'),
           ('Case', 'cases', 'name', 'status', 'New')]


@pytest.mark.parametrize('target,route,name,stage,default', OBJECTS)
def test_name_only_records_generate_distinct_ids(admin_client, org_a, target, route, name, stage, default):
    model = target_model(target)
    for payload in ({name: 'First'}, {name: 'Second', stage: ''}):
        result = admin_client.post(f'/api/{route}/', payload, format='json')
        assert result.status_code in (200, 201), result.data
    records = list(model.objects.filter(org=org_a))
    assert len(records) == 2
    assert len({r.id for r in records}) == 2
    assert all(getattr(r, name) in {'First', 'Second'} and getattr(r, stage) == default for r in records)
    rows = admin_client.get(f'/api/custom-fields/?catalog=true&target_model={target}').json()['properties']
    assert {r['key'] for r in rows if r['is_required']} == {'id', name}
    assert next(r for r in rows if r['key'] == 'id')['is_read_only']


@pytest.mark.parametrize('target,route,name,stage,default', OBJECTS)
def test_stage_requirements_survive_optional_policy(admin_client, org_a, target, route, name, stage, default):
    assert configure(admin_client, target, lambda rows: next(r for r in rows if r['key'] == default).update(required_fields=[name])).status_code == 200
    result = admin_client.post(f'/api/{route}/', {}, format='json')
    assert result.status_code == 400, result.data
    assert 'stage_requirements' in str(result.data)
    assert not target_model(target).objects.filter(org=org_a).exists()
    result = admin_client.post(f'/api/{route}/', {name: 'Stage requirement met'}, format='json')
    assert result.status_code in (200, 201), result.data


def test_custom_required_cannot_be_reenabled_but_stage_can_require_it(admin_client, org_a):
    payload = dict(target_model='Contact', key='reference', label='Reference', field_type='text', is_required=True)
    result = admin_client.post('/api/custom-fields/', payload, format='json')
    assert result.status_code == 201, result.data
    assert result.data['is_required'] is False
    # Even stale definitions no longer make a field globally required.
    CustomFieldDefinition.objects.filter(org=org_a, key='reference').update(is_required=True)
    result = admin_client.post('/api/contacts/', {'name': 'Optional custom value', 'custom_fields': {}}, format='json')
    assert result.status_code in (200, 201), result.data
    assert configure(admin_client, 'Contact', lambda rows: next(r for r in rows if r['key']=='QUALIFIED').update(required_fields=['custom_fields.reference'])).status_code == 200
    result = admin_client.post('/api/contacts/', {'name': 'Stage validation', 'stage':'QUALIFIED', 'custom_fields':{}}, format='json')
    assert result.status_code == 400
    assert 'stage_requirements' in str(result.data)


def test_optional_format_validation_and_id_protection(admin_client, org_a):
    assert admin_client.post('/api/contacts/', {'name': 'Invalid email', 'email': 'broken'}, format='json').status_code == 400
    assert admin_client.post('/api/accounts/', {'name': 'Invalid domain', 'website': 'broken'}, format='json').status_code == 400
    result = admin_client.post('/api/contacts/', {'name': 'ID check'}, format='json')
    assert result.status_code in (200, 201)
    contact = target_model('Contact').objects.get(org=org_a)
    original = contact.pk
    result = admin_client.patch(f'/api/contacts/{original}/', {'id': '11111111-1111-1111-1111-111111111111'}, format='json')
    assert result.status_code == 200, result.data
    contact.refresh_from_db()
    assert contact.pk == original


@pytest.mark.parametrize('target,route,name,stage,default', OBJECTS)
def test_forms_can_clear_optional_values(admin_client, org_a, target, route, name, stage, default):
    public_name = 'name' if target == 'Contact' else name
    payload = {public_name: 'Optional properties', stage: None, 'assigned_to': [], 'contacts': [], 'custom_fields': {}}
    if target in {'Contact', 'Account', 'Opportunity'}:
        payload.update(email=None, phone=None, language=None)
    if target == 'Account': payload['website'] = None
    if target == 'Contact': payload['source'] = None
    if target == 'Opportunity': payload.update(priority=None, lead_source=None, account=None)
    if target == 'Case': payload.update(priority=None, description=None, account=None)
    if target == 'Task': payload['priority'] = None
    response = admin_client.post(f'/api/{route}/', payload, format='json')
    assert response.status_code in (200, 201), response.data
    obj = target_model(target).objects.get(org=org_a)
    assert getattr(obj, name) == 'Optional properties'
    assert getattr(obj, stage) == default
    response = admin_client.patch(f'/api/{route}/{obj.pk}/', {public_name: 'Temporary name'}, format='json')
    assert response.status_code == 200, response.data
    response = admin_client.patch(f'/api/{route}/{obj.pk}/', payload, format='json')
    assert response.status_code == 200, response.data
    obj.refresh_from_db()
    assert getattr(obj, name) == 'Optional properties'


@pytest.mark.parametrize('target,route,name,stage,default', OBJECTS)
def test_names_are_required_on_create_and_edit(admin_client, org_a, target, route, name, stage, default):
    public_name = 'name' if target == 'Contact' else name
    for value in (None, '', '  '):
        assert admin_client.post(f'/api/{route}/', {public_name: value}, format='json').status_code == 400
    assert admin_client.post(f'/api/{route}/', {}, format='json').status_code == 400
    response = admin_client.post(f'/api/{route}/', {public_name: 'Keep name'}, format='json')
    assert response.status_code == 200, response.data
    obj = target_model(target).objects.get(org=org_a)
    for value in (None, '', '  '):
        assert admin_client.patch(f'/api/{route}/{obj.pk}/', {public_name: value}, format='json').status_code == 400
    obj.refresh_from_db()
    assert getattr(obj, name) == 'Keep name'
