from datetime import datetime, timezone
import pytest
from accounts.models import Account
from contacts.models import Contact

@pytest.mark.django_db
@pytest.mark.parametrize('model,route', [(Contact,'contacts'),(Account,'accounts')])
def test_calendar_range_and_org(admin_client, org_a, org_b, model, route):
    def create(org, hour):
        fields = {'first_name':'Calendar'} if model is Contact else {'name':f'Calendar {org.pk} {hour}'}
        return model.objects.create(org=org, appointment_at=datetime(2026,9,13,hour,tzinfo=timezone.utc), **fields)
    included = create(org_a,4)
    create(org_a,3)
    create(org_a,5)
    create(org_b,4)
    response = admin_client.get(f'/api/{route}/', {'calendar_start':'2026-09-13T04:00:00Z','calendar_end':'2026-09-13T05:00:00Z'})
    assert response.status_code == 200, response.data
    rows = response.data['results'] if model is Contact else response.data['active_accounts']['open_accounts']
    assert [str(r['id']) for r in rows] == [str(included.pk)]
    assert rows[0]['appointment_at']
    bad = admin_client.get(f'/api/{route}/', {'calendar_start':'invalid','calendar_end':'2026-09-13T05:00:00Z'})
    assert bad.status_code == 400

@pytest.mark.django_db
def test_company_appointment_save(admin_client, org_a):
    account = Account.objects.create(org=org_a,name='Appointment test')
    for value in ['2026-09-14T13:30:00Z', None]:
        response = admin_client.patch(f'/api/accounts/{account.pk}/', {'appointment_at':value}, format='json')
        assert response.status_code == 200, response.data
        account.refresh_from_db()
        assert (account.appointment_at is None) == (value is None)
