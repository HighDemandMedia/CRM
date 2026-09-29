"""Preserve tenant/permission contracts while reducing the page-load workload."""

import json
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from accounts.models import Account
from contacts.models import Contact
from opportunity.models import Opportunity
from common.models import CustomFieldDefinition
from common.testing import rls_org


@pytest.mark.django_db
@pytest.mark.parametrize("client_name", ["admin_client", "user_client"])
def test_ui_context_matches_individual_endpoints(request, client_name):
    client = request.getfixturevalue(client_name)
    response = client.get("/api/org/ui-context/")
    assert response.status_code == 200
    data = response.json()
    assert data["permissions"] == client.get("/api/permissions/me/").json()
    assert (
        data["property_layout"] == client.get("/api/property-layout/").json()["objects"]
    )
    assert (
        data["pipelines"]
        == client.get("/api/pipeline-settings/?include_rules=false").json()["pipelines"]
    )
    assert data["terminology"] == client.get("/api/org/settings/").json()["terminology"]
    assert response["Cache-Control"] == "private, no-store"


@pytest.mark.django_db
def test_ui_context_is_org_scoped_and_fresh(admin_client, org_a, org_b):
    with rls_org(org_b):
        CustomFieldDefinition.objects.create(
            org=org_b,
            target_model="Contact",
            key="custom_secret",
            label="Other organization",
            field_type="text",
        )
    before = admin_client.get("/api/org/ui-context/").json()
    assert "custom_secret" not in json.dumps(before)
    org_a.terminology = {"account.plural": "Customers"}
    org_a.save()
    CustomFieldDefinition.objects.create(
        org=org_a,
        target_model="Contact",
        key="custom_new",
        label="New property",
        field_type="text",
    )
    after = admin_client.get("/api/org/ui-context/").json()
    assert after["terminology"]["account.plural"] == "Customers"
    assert "custom_new" in json.dumps(after)
    assert "custom_secret" not in json.dumps(after)


@pytest.mark.django_db
def test_ui_context_requires_login(unauthenticated_client):
    assert unauthenticated_client.get("/api/org/ui-context/").status_code in (401, 403)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint, key",
    [
        ("accounts", "active_accounts"),
        ("opportunities", "opportunities"),
        ("contacts", "results"),
    ],
)
def test_compact_lists_keep_records_and_reduce_queries(
    admin_client, org_a, org_b, endpoint, key
):
    for i in range(8):
        company = Account.objects.create(org=org_a, name=f"Company {i}")
        contact = Contact.objects.create(
            org=org_a, first_name=f"Person {i}", email=f"person{i}@example.com"
        )
        company.contacts.add(contact)
        deal = Opportunity.objects.create(org=org_a, name=f"Deal {i}", account=company)
        deal.contacts.add(contact)
    with rls_org(org_b):
        Account.objects.create(org=org_b, name="Hidden organization record")
        Contact.objects.create(org=org_b, first_name="Hidden person")
        Opportunity.objects.create(org=org_b, name="Hidden deal")
    with CaptureQueriesContext(connection) as full_queries:
        full = admin_client.get(f"/api/{endpoint}/?limit=25")
    with CaptureQueriesContext(connection) as compact_queries:
        compact = admin_client.get(f"/api/{endpoint}/?limit=25&compact=true")
    assert full.status_code == compact.status_code == 200, compact.data
    full_rows, compact_rows = full.json()[key], compact.json()[key]
    if endpoint == "accounts":
        full_rows, compact_rows = (
            full_rows["open_accounts"],
            compact_rows["open_accounts"],
        )
    assert [r["id"] for r in full_rows] == [r["id"] for r in compact_rows]
    for old, new in zip(full_rows, compact_rows):
        for field in ("id", "name", "stage", "custom_fields", "last_activity_at"):
            if field in old:
                assert new[field] == old[field]
    assert "Hidden" not in compact.content.decode()
    assert len(compact.content) < len(full.content)
    assert len(compact_queries) <= len(full_queries)
    if endpoint != "contacts":
        assert len(compact_queries) < len(full_queries) / 2
    print(
        f"{endpoint}: queries {len(full_queries)} -> {len(compact_queries)}; bytes {len(full.content)} -> {len(compact.content)}"
    )


@pytest.mark.django_db
def test_ui_context_rejects_org_api_key(unauthenticated_client, org_a, admin_profile):
    response = unauthenticated_client.get(
        "/api/org/ui-context/", HTTP_TOKEN=org_a.api_key
    )
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_compact_lists_respect_own_scope_and_hidden_relations(
    user_client, user_profile, org_a
):
    from common.models import CRMRole
    from common.rbac import default_rules

    role = CRMRole.objects.create(
        org=org_a, name="Own records", scope="own", rules=default_rules("own")
    )
    user_profile.access_role = role
    user_profile.save()
    visible_company = Account.objects.create(org=org_a, name="Visible company")
    visible_company.assigned_to.add(user_profile)
    hidden_company = Account.objects.create(org=org_a, name="Hidden company")
    visible_contact = Contact.objects.create(org=org_a, first_name="Visible contact")
    visible_contact.assigned_to.add(user_profile)
    hidden_contact = Contact.objects.create(org=org_a, first_name="Hidden contact")
    visible_company.contacts.add(visible_contact, hidden_contact)
    visible_deal = Opportunity.objects.create(
        org=org_a, name="Visible deal", account=hidden_company
    )
    visible_deal.assigned_to.add(user_profile)
    visible_deal.contacts.add(visible_contact, hidden_contact)
    Opportunity.objects.create(org=org_a, name="Hidden deal")
    for endpoint in ("accounts", "contacts", "opportunities"):
        for choices in ("true", "false"):
            response = user_client.get(
                f"/api/{endpoint}/?compact=true&include_choices={choices}"
            )
            assert response.status_code == 200, response.data
            payload = response.content.decode()
            assert "Visible" in payload
            assert "Hidden" not in payload
