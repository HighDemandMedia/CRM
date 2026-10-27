from decimal import Decimal

import pytest

from contacts.models import Contact
from opportunity.models import Opportunity

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("currency", ["USD", "EUR", None])
def test_contact_detail_preserves_associated_deal_currency(
    admin_client, org_a, currency
):
    contact = Contact.objects.create(first_name="Currency test", org=org_a)
    deal = Opportunity.objects.create(
        name="Associated deal", org=org_a, amount=125, currency=currency
    )
    deal.contacts.add(contact)

    response = admin_client.get(f"/api/contacts/{contact.pk}/")

    assert response.status_code == 200
    associated_deal = next(
        row for row in response.data["opportunities"] if row["id"] == str(deal.pk)
    )
    assert associated_deal["currency"] == currency
    assert Decimal(str(associated_deal["amount"])) == Decimal("125")


def test_pipeline_totals_by_currency(admin_client, org_a):
    contact = Contact.objects.create(first_name="Value test", org=org_a)
    for amount, currency in [
        (100, "USD"),
        (50, "USD"),
        (20, "EUR"),
        (0, "GBP"),
        (None, None),
    ]:
        deal = Opportunity.objects.create(
            name="Deal", org=org_a, amount=amount, currency=currency
        )
        deal.contacts.add(contact)
    rows = admin_client.get("/api/contacts/?include_deal_values=true").data["results"]
    row = next(row for row in rows if str(row["id"]) == str(contact.id))
    totals = {value["currency"]: value["amount"] for value in row["deal_values"]}
    assert Decimal(totals["USD"]) == Decimal("150")
    assert Decimal(totals["EUR"]) == Decimal("20")
    assert Decimal(totals["GBP"]) == 0
    assert totals[""] is None


def test_only_visible_deals_count(
    user_client, user_profile, admin_profile, regular_user, org_a
):
    contact = Contact.objects.create(first_name="Visible contact", org=org_a)
    contact.assigned_to.add(user_profile)
    hidden = Opportunity.objects.create(
        name="Hidden", org=org_a, amount=900, currency="USD"
    )
    hidden.contacts.add(contact)
    visible = Opportunity.objects.create(
        name="Visible", org=org_a, amount=25, currency="USD"
    )
    visible.contacts.add(contact)
    visible.assigned_to.add(user_profile, admin_profile)
    Opportunity.objects.filter(pk=visible.pk).update(created_by=regular_user)
    rows = user_client.get("/api/contacts/?include_deal_values=true").data["results"]
    row = next(row for row in rows if str(row["id"]) == str(contact.id))
    assert len(row["deal_values"]) == 1
    assert Decimal(row["deal_values"][0]["amount"]) == 25


def test_no_deals_is_empty_and_values_are_opt_in(admin_client, org_a):
    contact = Contact.objects.create(first_name="No deals", org=org_a)
    rows = admin_client.get("/api/contacts/?include_deal_values=true").data["results"]
    assert (
        next(row for row in rows if str(row["id"]) == str(contact.id))["deal_values"]
        == []
    )
    rows = admin_client.get("/api/contacts/").data["results"]
    assert "deal_values" not in next(
        row for row in rows if str(row["id"]) == str(contact.id)
    )
