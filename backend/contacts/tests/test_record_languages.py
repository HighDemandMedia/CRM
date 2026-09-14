import pytest
from accounts.models import Account
from contacts.models import Contact
from opportunity.models import Opportunity


@pytest.mark.django_db
@pytest.mark.parametrize('model,route', [(Contact, 'contacts'), (Account, 'accounts'), (Opportunity, 'opportunities')])
def test_language_update_and_clear(admin_client, org_a, model, route):
    fields = {'first_name': 'Language test'} if model is Contact else {'name': 'Language test'}
    record = model.objects.create(org=org_a, **fields)
    url = f'/api/{route}/{record.pk}/'
    for language in ['Spanish', 'English', '']:
        response = admin_client.patch(url, {'language': language}, format='json')
        assert response.status_code == 200, response.data
        record.refresh_from_db()
        assert record.language == language
    response = admin_client.patch(url, {'language': 'invalid-language'}, format='json')
    assert response.status_code == 400
