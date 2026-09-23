import pytest
from common.models import CustomFieldDefinition
from contacts.models import Contact

URL = '/api/custom-fields/'

@pytest.mark.django_db
def test_catalog_counts_values_and_associations_without_cross_org_leak(admin_client, org_a, org_b, admin_profile):
    a = Contact.objects.create(org=org_a, first_name='One', email='one@example.com', custom_fields={'rating': 0, 'subscribed': False})
    b = Contact.objects.create(org=org_a, first_name='Two', email='', custom_fields={'rating': None, 'subscribed': ''})
    Contact.objects.create(org=org_b, first_name='Other', email='other@example.com', custom_fields={'rating': 1})
    a.assigned_to.add(admin_profile)
    for key, kind in [('rating', 'number'), ('subscribed', 'checkbox')]:
        CustomFieldDefinition.objects.create(org=org_a, target_model='Contact', key=key, label=key, field_type=kind)
    response = admin_client.get(URL + '?catalog=true&target_model=Contact')
    assert response.status_code == 200
    body = response.json()
    rows = {row['key']: row for row in body['properties']}
    assert body['record_count'] == 2
    assert rows['first_name']['is_system'] is True
    assert rows['phone']['is_required'] is False
    assert rows['email']['usage_count'] == 1
    assert rows['assigned_to']['usage_count'] == 1
    assert rows['rating']['usage_count'] == 1
    assert rows['subscribed']['usage_count'] == 1
    assert rows['rating']['is_system'] is False
    assert 'custom_fields' not in rows and 'org' not in rows

@pytest.mark.django_db
@pytest.mark.parametrize('target', ['Contact', 'Account', 'Opportunity', 'Task', 'Case', 'Lead', 'Invoice', 'Estimate', 'RecurringInvoice'])
def test_catalog_supports_all_objects(admin_client, target):
    response = admin_client.get(URL + '?catalog=true&target_model=' + target)
    assert response.status_code == 200
    assert response.json()['properties']

@pytest.mark.django_db
def test_catalog_invalid_and_unauthorized(user_client, admin_client):
    assert user_client.get(URL + '?catalog=true&target_model=Contact').status_code == 403
    assert admin_client.get(URL + '?catalog=true&target_model=Unknown').status_code == 400

@pytest.mark.django_db
def test_system_keys_cannot_be_overwritten_and_custom_creation_is_scoped(admin_client):
    payload = {'target_model': 'Contact', 'key': 'phone', 'label': 'Renamed phone', 'field_type': 'text'}
    assert admin_client.post(URL, payload, format='json').status_code == 400
    payload.update(key='custom_reference', label='Reference', is_required=True)
    result = admin_client.post(URL, payload, format='json')
    assert result.status_code == 201
    assert result.json()['is_required'] is False
    companies = admin_client.get(URL + '?catalog=true&target_model=Account').json()
    assert not any(row['key'] == 'custom_reference' for row in companies['properties'])
