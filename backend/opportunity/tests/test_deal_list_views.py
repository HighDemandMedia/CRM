import pytest
from accounts.models import Account
from contacts.models import Contact
from opportunity.models import Opportunity

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "sort",
    [
        "name",
        "amount",
        "stage_label",
        "closed_on",
        "owner",
        "priority_label",
        "lead_source_label",
        "account",
        "contacts",
        "address_line",
        "city",
        "state",
        "postcode",
        "country_label",
        "created_at",
        "updated_at",
    ],
)
def test_deal_list_filters_and_sort(admin_client, admin_profile, org_a, org_b, sort):
    company = Account.objects.create(name="Partner", org=org_a)
    contact = Contact.objects.create(first_name="Alice", org=org_a)
    deal = Opportunity.objects.create(
        name="Find me",
        org=org_a,
        account=company,
        amount=500,
        stage="PROPOSAL",
        priority="HIGH",
        city="Miami",
        lead_source="META",
    )
    deal.contacts.add(contact)
    deal.assigned_to.add(admin_profile)
    Opportunity.objects.create(
        name="Hidden",
        org=org_b,
        amount=500,
        stage="PROPOSAL",
        priority="HIGH",
        city="Miami",
    )
    response = admin_client.get(
        "/api/opportunities/",
        {
            "search": "Alice",
            "contacts": str(contact.pk),
            "assigned_to": str(admin_profile.pk),
            "account": str(company.pk),
            "stage": "PROPOSAL",
            "priority": "HIGH",
            "city": "Miami",
            "sort": sort,
            "limit": 1,
        },
    )
    assert response.status_code == 200, response.data
    assert response.data["totals"]["count"] == 1
    assert str(response.data["opportunities"][0]["id"]) == str(deal.pk)


def test_numeric_sort_and_zero_filter(admin_client, org_a):
    for name, amount in [("Ten", 10), ("Two", 2), ("Zero", 0)]:
        Opportunity.objects.create(name=name, amount=amount, org=org_a)
    response = admin_client.get(
        "/api/opportunities/",
        {"sort": "amount", "direction": "asc", "limit": 1, "offset": 1},
    )
    assert response.data["opportunities"][0]["name"] == "Two"
    response = admin_client.get("/api/opportunities/", {"amount__lte": "0"})
    assert response.data["totals"]["count"] == 1


def test_move_updates_stage_and_preserves_other_properties(admin_client, org_a):
    deal = Opportunity.objects.create(
        name="Move me",
        org=org_a,
        stage="PROSPECTING",
        priority="HIGH",
        lead_source="GOOGLE",
    )
    response = admin_client.patch(
        f"/api/opportunities/{deal.pk}/move/",
        {"column_id": "CLOSED_WON"},
        format="json",
    )
    assert response.status_code == 200, response.data
    deal.refresh_from_db()
    assert deal.stage == "CLOSED_WON"
    assert deal.priority == "HIGH" and deal.lead_source == "GOOGLE"
    assert deal.stage_changed_at is not None
