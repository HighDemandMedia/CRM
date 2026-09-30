from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from common.models import CustomFieldDefinition, Org, Profile
from common.rbac import default_rules
from common.serializer import OrgAwareRefreshToken
from common.testing import _make_authenticated_client, rls_org
from contacts.models import Contact

pytestmark = pytest.mark.django_db


@pytest.fixture
def demo(user_profile, org_a):
    user_profile.is_demo = True
    user_profile.role = 'ADMIN'
    user_profile.save()
    return user_profile, _make_authenticated_client(user_profile.user, org_a, user_profile)


def test_demo_claim_and_ready_pages(demo):
    profile, client = demo
    token = OrgAwareRefreshToken.for_user_and_org(profile.user, profile.org, profile)
    assert token['is_demo'] is True and token.access_token['is_demo'] is True
    assert token['role'] == 'ADMIN'
    for url in ('/api/webforms/', '/api/contacts/', '/api/accounts/', '/api/opportunities/', '/api/tasks/', '/api/cases/', '/api/pipeline-settings/', '/api/custom-fields/?catalog=true&target_model=Contact', '/api/roles/', '/api/teams/', '/api/users/'):
        response = client.get(url)
        assert response.status_code == 200, (url, response.content)


@pytest.mark.parametrize('path', ['/api/leads/', '/api/invoices/', '/api/documents/', '/api/cases/solutions/'])
def test_demo_cannot_open_unfinished_modules(demo, path):
    response = demo[1].get(path)
    assert response.status_code == 403
    assert 'customer demo' in response.json()['detail']


def test_demo_cannot_cross_tenants(demo, org_b):
    profile, client = demo
    with rls_org(org_b):
        other = Contact.objects.create(org=org_b, first_name='Private')
    assert client.get(f'/api/contacts/{other.pk}/').status_code == 404
    assert client.post('/api/auth/switch-org/', {'org_id': str(org_b.pk)}, format='json').status_code == 403
    assert client.post('/api/org/', {'name': 'Escape demo'}, format='json').status_code == 403
    assert client.get('/api/auth/me/').data['organizations'][0]['is_demo'] is True


def test_demo_can_edit_and_delete_fictional_records(demo, org_a):
    profile, client = demo
    contact = Contact.objects.create(org=org_a, first_name='Fictional', created_by=profile.user)
    contact.assigned_to.add(profile)
    response = client.patch(f'/api/contacts/{contact.pk}/', {'first_name': 'Edited'}, format='json')
    assert response.status_code == 200, response.content
    contact.refresh_from_db()
    assert contact.first_name == 'Edited'
    assert client.delete(f'/api/contacts/{contact.pk}/').status_code == 200
    assert not Contact.objects.filter(pk=contact.pk).exists()


def test_normal_user_also_has_customer_module_visibility(admin_profile, admin_client):
    token = OrgAwareRefreshToken.for_user_and_org(admin_profile.user, admin_profile.org, admin_profile)
    assert token['is_demo'] is False
    assert admin_client.get('/api/leads/').status_code == 403


def test_setup_is_separate_and_preserves_repeat_edits(settings, admin_user, org_a):
    settings.DEBUG = True
    existing_name = org_a.name
    with patch('common.management.commands.setup_customer_demo.call_command') as seed:
        call_command('setup_customer_demo', owner_email=admin_user.email, stdout=StringIO())
        profile = Profile.objects.select_related('org').get(user__email='demo@example.com')
        assert profile.is_demo and profile.role == 'ADMIN' and not profile.is_super_admin
        assert profile.org_id != org_a.pk and profile.org.owner_id == admin_user.pk
        assert Profile.objects.filter(user=profile.user).count() == 1
        profile.org.name = 'Customer demonstration'
        profile.org.save()
        call_command('setup_customer_demo', owner_email=admin_user.email, stdout=StringIO())
        assert seed.call_count == 1
        profile.org.refresh_from_db()
        assert profile.org.name == 'Customer demonstration'
    org_a.refresh_from_db()
    assert org_a.name == existing_name


def test_setup_rejects_existing_non_demo_user(settings, admin_user, regular_user):
    settings.DEBUG = True
    before = Org.objects.count()
    with pytest.raises(CommandError):
        call_command('setup_customer_demo', owner_email=admin_user.email, demo_email=regular_user.email, stdout=StringIO())
    assert Org.objects.count() == before


def test_setup_is_local_only(settings, admin_user):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command('setup_customer_demo', owner_email=admin_user.email, stdout=StringIO())


def test_demo_admin_can_configure_own_organization(demo, org_a, org_b):
    profile, client = demo
    result = client.post('/api/custom-fields/', {
        'target_model': 'Contact', 'key': 'demo_reference', 'label': 'Demo reference', 'field_type': 'text'
    }, format='json')
    assert result.status_code == 201, result.content
    assert CustomFieldDefinition.objects.get(pk=result.data['id']).org_id == org_a.pk
    assert client.post('/api/roles/', {'name': 'Demo tester', 'scope': 'organization', 'rules': default_rules('organization')}, format='json').status_code == 201
    assert client.get('/api/roles/export/contacts/').status_code == 200
    profile.user.refresh_from_db()
    assert not profile.user.is_staff and not profile.user.is_superuser
