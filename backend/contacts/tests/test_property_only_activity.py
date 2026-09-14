import pytest
from common.models import Activity
from contacts.models import Contact

@pytest.mark.django_db
def test_open_does_not_log_and_property_change_does(admin_client, org_a):
    contact = Contact.objects.create(org=org_a, first_name='Activity test')
    url = f'/api/contacts/{contact.pk}/'
    # Previously saved view entries must no longer appear in the profile.
    Activity.objects.create(org=org_a,entity_type='Contact',entity_id=contact.pk,action='VIEW',description='Contact opened')
    before = Activity.objects.filter(entity_id=contact.pk).count()
    for _ in range(2):
        response=admin_client.get(url)
        assert response.status_code == 200
        assert all(entry['action'] != 'VIEW' for entry in response.data['history'])
    assert Activity.objects.filter(entity_id=contact.pk).count() == before
    response=admin_client.patch(url,{'city':'Miami'},format='json')
    assert response.status_code == 200, response.data
    assert Activity.objects.filter(entity_id=contact.pk,action='UPDATE',metadata__changes__city__after='Miami').exists()
