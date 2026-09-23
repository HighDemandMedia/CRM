import pytest
from accounts.models import Account

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('extra', [{}, {'website': ''}, {'website': None}, {'website': '   '}])
def test_company_creation_accepts_optional_domain(admin_client, org_a, extra):
    response = admin_client.post('/api/accounts/', {'name': 'Missing domain', **extra}, format='json')
    assert response.status_code == 200, response.data
    assert Account.objects.filter(org=org_a, name='Missing domain').exists()


def test_valid_domain_and_partial_updates(admin_client, org_a):
    response = admin_client.post('/api/accounts/', {'name': 'Domain Company', 'website': 'https://example.com'}, format='json')
    assert response.status_code == 200, response.data
    account = Account.objects.get(org=org_a, name='Domain Company')
    url = f'/api/accounts/{account.pk}/'
    for empty in ('', None):
        assert admin_client.patch(url, {'website': empty}, format='json').status_code == 200
    assert admin_client.patch(url, {'city': 'Miami'}, format='json').status_code == 200
    account.refresh_from_db()
    assert account.website is None
    assert account.city == 'Miami'


def test_legacy_company_can_receive_unrelated_partial_update(admin_client, org_a):
    account = Account.objects.create(org=org_a, name='Legacy')
    response = admin_client.patch(f'/api/accounts/{account.pk}/', {'city': 'Miami'}, format='json')
    assert response.status_code == 200


def test_domain_is_optional_in_catalog(admin_client):
    rows = admin_client.get('/api/custom-fields/?catalog=true&target_model=Account').json()['properties']
    assert next(row for row in rows if row['key'] == 'website')['is_required'] is False
