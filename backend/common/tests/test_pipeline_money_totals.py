from decimal import Decimal

import pytest

from accounts.models import Account
from contacts.models import Contact
from opportunity.models import Opportunity

pytestmark = pytest.mark.django_db


def amounts(rows):
    return {row['currency']: Decimal(row['amount']) for row in rows}


def test_contact_total_is_filtered_unpaginated_and_counts_shared_deal_once(admin_client, org_a, org_b):
    contacts = [Contact.objects.create(first_name=f'Total {i}', org=org_a, stage='LEAD') for i in range(3)]
    for amount, currency in [(100, 'USD'), (100, 'USD'), (20, 'EUR')]:
        deal = Opportunity.objects.create(name='Shared deal', org=org_a, amount=amount, currency=currency)
        deal.contacts.add(*contacts)
    other = Opportunity.objects.create(name='Other org', org=org_b, amount=999, currency='USD')
    other.contacts.add(*contacts)
    for offset in (0, 1):
        response = admin_client.get(f'/api/contacts/?include_pipeline_totals=true&stage=LEAD&limit=1&offset={offset}')
        assert response.status_code == 200
        assert amounts(response.data['money_totals']) == {'EUR': Decimal(20), 'USD': Decimal(200)}
    response = admin_client.get('/api/contacts/?include_pipeline_totals=true&stage=LOST')
    assert response.data['money_totals'] == []


def test_deal_total_preserves_currency_and_filters_before_pagination(admin_client, org_a, org_b):
    for org, stage, value, currency in [(org_a, 'PROPOSAL', 100, 'USD'), (org_a, 'PROPOSAL', 100, 'USD'), (org_a, 'PROPOSAL', 30, 'EUR'), (org_a, 'PROSPECTING', 999, 'USD'), (org_b, 'PROPOSAL', 999, 'USD')]:
        Opportunity.objects.create(name='Total', org=org, stage=stage, amount=value, currency=currency)
    response = admin_client.get('/api/opportunities/?include_pipeline_totals=true&stage=PROPOSAL&limit=1')
    assert response.status_code == 200
    assert amounts(response.data['totals']['money_totals']) == {'EUR': Decimal(30), 'USD': Decimal(200)}


def test_company_total_excludes_inactive_other_stages_and_other_orgs(admin_client, org_a, org_b):
    for org, stage, active, value in [(org_a, 'LEAD', True, 100), (org_a, 'LEAD', True, 100), (org_a, 'LOST', True, 999), (org_a, 'LEAD', False, 999), (org_b, 'LEAD', True, 999)]:
        Account.objects.create(name=f'Total {Account.objects.count()}', org=org, stage=stage, is_active=active, annual_revenue=value, currency='USD')
    response = admin_client.get('/api/accounts/?include_pipeline_totals=true&stage=LEAD&limit=1')
    assert response.status_code == 200
    assert amounts(response.data['money_totals']) == {'USD': Decimal(200)}


def test_contact_total_excludes_unassigned_deals(user_client, user_profile, org_a):
    contact = Contact.objects.create(first_name='Mine', org=org_a, stage='LEAD')
    contact.assigned_to.add(user_profile)
    for visible, value in [(True, 25), (False, 999)]:
        deal = Opportunity.objects.create(name='Deal', org=org_a, amount=value, currency='USD')
        deal.contacts.add(contact)
        if visible:
            deal.assigned_to.add(user_profile)
    response = user_client.get('/api/contacts/?include_pipeline_totals=true&stage=LEAD')
    assert response.status_code == 200
    assert amounts(response.data['money_totals']) == {'USD': Decimal(25)}
