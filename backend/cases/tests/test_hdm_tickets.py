from datetime import timedelta
import pytest
from django.utils import timezone
from cases.models import Case
from opportunity.models import Opportunity

pytestmark = pytest.mark.django_db


def test_numbers_survive_deletion(org_a):
    first = Case.objects.create(org=org_a, name='First', status='New', priority='Normal')
    number = first.ticket_number
    first.delete()
    second = Case.objects.create(org=org_a, name='Second', status='New', priority='Normal')
    assert second.ticket_number == number + 1
    assert second.ticket_code == f'TKT-{number+1:04d}'


def test_resolve_requires_note_and_reopen_keeps_history(admin_client, case_a):
    url = f'/api/cases/{case_a.id}/'
    assert admin_client.patch(url, {'status': 'Resolved'}, format='json').status_code == 400
    response = admin_client.patch(url, {'status':'Resolved','resolution_note':'Replaced broken connection.'}, format='json')
    assert response.status_code == 200, response.data
    case_a.refresh_from_db()
    assert case_a.resolved_at is not None
    response = admin_client.patch(url, {'status':'New'}, format='json')
    assert response.status_code == 200, response.data
    case_a.refresh_from_db()
    assert case_a.resolved_at is None
    assert case_a.resolution_note == 'Replaced broken connection.'


def test_properties_and_overdue(admin_client, case_a):
    due = timezone.now() - timedelta(hours=2)
    response = admin_client.patch(f'/api/cases/{case_a.id}/', {'category':'Service','source':'Call','due_at':due.isoformat(),'waiting_reason':'Internal'}, format='json')
    assert response.status_code == 200, response.data
    response = admin_client.get('/api/cases/?overdue=true&slim=true')
    assert response.status_code == 200, response.data
    assert str(case_a.id) in [str(row['id']) for row in response.data['cases']]
    admin_client.patch(f'/api/cases/{case_a.id}/', {'status':'Resolved','resolution_note':'Done'}, format='json')
    response = admin_client.get('/api/cases/?overdue=true&slim=true')
    assert str(case_a.id) not in [str(row['id']) for row in response.data['cases']]


def test_other_org_deal_refused(admin_client, case_a, org_b):
    other = Opportunity.objects.create(org=org_b, name='Private', stage='PROSPECTING')
    response = admin_client.patch(f'/api/cases/{case_a.id}/', {'deal':str(other.id)}, format='json')
    assert response.status_code == 400
    case_a.refresh_from_db()
    assert case_a.deal_id is None


def test_search_ticket_number(admin_client, case_a):
    response = admin_client.get('/api/cases/', {'search': case_a.ticket_code, 'slim':'true'})
    assert response.status_code == 200
    assert [str(row['id']) for row in response.data['cases']] == [str(case_a.id)]


def test_deal_associations_disabled(admin_client, case_a):
    response = admin_client.patch(f'/api/cases/{case_a.id}/', {'deal': '00000000-0000-0000-0000-000000000001'}, format='json')
    assert response.status_code == 400
    assert 'deal' in response.data['errors']
