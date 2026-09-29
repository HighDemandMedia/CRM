"""Board batching preserves list visibility, paging and money totals."""
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from accounts.models import Account
from contacts.models import Contact
from opportunity.models import Opportunity
from common.models import CRMRole
from common.pipeline_settings import stages_for
from common.rbac import default_rules
from common.testing import rls_org

pytestmark = pytest.mark.django_db


def list_rows(data, endpoint):
    if endpoint == "accounts":
        return data["active_accounts"]["open_accounts"]
    return data["results" if endpoint == "contacts" else "opportunities"]


def list_count(data, endpoint):
    if endpoint == "accounts":
        return data["active_accounts"]["open_accounts_count"]
    return data["count"] if endpoint == "contacts" else data["totals"]["count"]


def list_money(data, endpoint):
    return data["totals"]["money_totals"] if endpoint == "opportunities" else data["money_totals"]


@pytest.mark.parametrize("endpoint,model", [("accounts", Account), ("contacts", Contact), ("opportunities", Opportunity)])
@pytest.mark.parametrize("own", [False, True])
def test_board_matches_stage_lists_and_reduces_queries(admin_client, user_client, user_profile, org_a, org_b, endpoint, model, own):
    client = user_client if own else admin_client
    if own:
        role = CRMRole.objects.create(org=org_a, name="Own", scope="own", rules=default_rules("own"))
        user_profile.access_role = role
        user_profile.save()
    stages = stages_for(org_a, model.__name__)
    custom = {**stages[0], "key": "CUSTOM_REVIEW", "label": "Review", "order": len(stages)}
    org_a.pipeline_settings = {model.__name__: [*stages, custom]}
    org_a.save()
    stages.append(custom)
    for stage in stages:
        for i in range(3):
            data = {"org": org_a, "stage": stage["key"], "first_name" if model == Contact else "name": f"Match {stage['key']} {i}"}
            if model != Contact:
                data.update({"currency": "EUR" if i == 2 else "USD", "annual_revenue" if model == Account else "amount": 20 + i})
            row = model.objects.create(**data)
            row.assigned_to.add(user_profile)
            if model == Contact:
                deal = Opportunity.objects.create(org=org_a, name="Shared", amount=50, currency="USD")
                deal.contacts.add(row)
                deal.assigned_to.add(user_profile)
    hidden = model.objects.create(org=org_a, stage=stages[0]["key"], **{"first_name" if model == Contact else "name": "Secret"})
    with rls_org(org_b):
        model.objects.create(org=org_b, stage=stages[0]["key"], **{"first_name" if model == Contact else "name": "Other tenant"})
    # Same filters, including a nonzero offset for only one column.
    query = {"compact": "true", "include_choices": "false", "include_pipeline_totals": "true", "include_deal_values": "true", "limit": 2, "search": "Match"}
    with CaptureQueriesContext(connection) as old_queries:
        expected = []
        for i, stage in enumerate(stages):
            response = client.get(f"/api/{endpoint}/", {**query, "stage": stage["key"], "offset": 1 if i == 0 else 0})
            assert response.status_code == 200, response.data
            expected.append(response.json())
    with CaptureQueriesContext(connection) as new_queries:
        response = client.get(f"/api/{endpoint}/", {**query, "board": "true", f'{stages[0]["key"]}_offset': 1})
        assert response.status_code == 200, response.data
    board = response.json()["board"]
    assert [c["key"] for c in board] == [s["key"] for s in stages]
    for column, previous in zip(board, expected):
        assert column["results"] == list_rows(previous, endpoint)
        assert column["count"] == list_count(previous, endpoint)
        assert column["money_totals"] == list_money(previous, endpoint)
    assert len(new_queries) < len(old_queries) / 2
    print(f'{endpoint} own={own}: {len(old_queries)} queries -> {len(new_queries)}')
    unfiltered = client.get(f"/api/{endpoint}/", {**query, "board": "true", "search": ""})
    assert "Other tenant" not in unfiltered.content.decode()
    if own:
        assert str(hidden.pk) not in unfiltered.content.decode()
    selected = client.get(f"/api/{endpoint}/", {**query, "board": "true", "stage": custom["key"], f'{custom["key"]}_offset': 100})
    assert len(selected.json()["board"]) == 1
    assert selected.json()["board"][0]["results"] == []
    assert selected.json()["board"][0]["count"] == 3


def test_contact_board_counts_shared_deal_once_and_keeps_empty_stages(admin_client, org_a):
    contacts = [Contact.objects.create(org=org_a, first_name=f"Person {i}", stage="LEAD") for i in range(3)]
    deal = Opportunity.objects.create(org=org_a, name="Shared", amount=75, currency="USD")
    deal.contacts.add(*contacts)
    response = admin_client.get('/api/contacts/', {"board": "true", "include_pipeline_totals": "true", "limit": 1, "LEAD_offset": -9})
    assert response.status_code == 200
    lead = next(c for c in response.json()["board"] if c["key"] == "LEAD")
    assert lead["offset"] == 0
    assert len(lead["results"]) == 1
    assert lead["count"] == 3
    assert float(lead["money_totals"][0]["amount"]) == 75
    assert float(response.json()["money_totals"][0]["amount"]) == 75
    assert all(c["results"] == [] and c["money_totals"] == [] for c in response.json()["board"] if c["key"] != "LEAD")


@pytest.mark.parametrize("endpoint", ["accounts", "contacts", "opportunities"])
def test_board_requires_authentication(unauthenticated_client, endpoint):
    assert unauthenticated_client.get(f'/api/{endpoint}/?board=true').status_code in (401, 403)
