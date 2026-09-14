import pytest

from accounts.models import Account
from common.models import Tags
from contacts.models import Contact

pytestmark = pytest.mark.django_db


def test_company_properties_and_contacts(admin_client, org_a, org_b, admin_profile):
    contact = Contact.objects.create(first_name="Linked", org=org_a)
    foreign = Contact.objects.create(first_name="Foreign", org=org_b)
    tag = Tags.objects.create(name="Company tag", color="blue", org=org_a)
    payload = {
        "name": "Company properties",
        "phone": "3055550188",
        "email": "company@example.com",
        "preferred_communication_channel": "SMS",
        "tag_ids": [str(tag.pk)],
        "website": "https://example.com",
        "source": "META",
        "pages": [{"name": "Social", "url": "https://example.com/social"}],
        "number_of_employees": 12,
        "annual_revenue": "1000.25",
        "contacts": [str(contact.pk)],
        "assigned_to": [str(admin_profile.pk)],
    }
    response = admin_client.post("/api/accounts/", payload, format="json")
    assert response.status_code == 200, response.data
    account = Account.objects.get(name=payload["name"], org=org_a)
    assert account.phone == payload["phone"]
    assert account.email == payload["email"]
    assert account.preferred_communication_channel == "SMS"
    assert account.tags.filter(pk=tag.pk).exists()
    assert account.pages == payload["pages"]
    assert list(account.contacts.all()) == [contact]
    assert contact.account_contacts.filter(pk=account.pk).exists()
    url = f"/api/accounts/{account.pk}/"
    response = admin_client.patch(url, {"source": "GOOGLE"}, format="json")
    assert response.status_code == 200, response.data
    account.refresh_from_db()
    assert account.source == "GOOGLE"
    assert account.contacts.filter(pk=contact.pk).exists()
    assert account.assigned_to.filter(pk=admin_profile.pk).exists()
    response = admin_client.patch(url, {"contacts": [str(foreign.pk)]}, format="json")
    assert response.status_code == 400
    assert account.contacts.filter(pk=contact.pk).exists()
    response = admin_client.patch(url, {"pages": [], "contacts": []}, format="json")
    assert response.status_code == 200, response.data
    account.refresh_from_db()
    response = admin_client.patch(url, {"preferred_communication_channel":"EMAIL", "phone":"", "email":"", "tag_ids":[], "assigned_to":[]}, format="json")
    assert response.status_code == 200, response.data
    account.refresh_from_db()
    assert account.preferred_communication_channel == 'EMAIL'
    assert not account.tags.exists() and not account.assigned_to.exists()
    assert not account.phone and not account.email
    assert account.pages == []
    assert not account.contacts.exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("pages", [{"name": "Bad", "url": "javascript:alert(1)"}]),
        ("pages", {}),
        ("source", "INVALID"),
        ("preferred_communication_channel", "INVALID"),
        ("annual_revenue", -1),
        ("number_of_employees", -1),
    ],
)
def test_invalid_company_properties(admin_client, field, value):
    response = admin_client.post(
        "/api/accounts/", {"name": "Invalid company", field: value}, format="json"
    )
    assert response.status_code == 400, response.data


@pytest.mark.parametrize(
    "sort",
    [
        "name",
        "website",
        "owner",
        "industry",
        "number_of_employees",
        "annual_revenue",
        "source_label",
        "country_display",
        "contacts",
        "pages",
        "created_at",
        "updated_at",
    ],
)
def test_company_filters_and_sort(admin_client, org_a, org_b, admin_profile, sort):
    a = Account.objects.create(
        name="Alpha",
        org=org_a,
        source="META",
        number_of_employees=12,
        country="US",
        pages=[{"name": "Jobs", "url": "https://example.com/jobs"}],
    )
    a.assigned_to.add(admin_profile)
    a.contacts.add(Contact.objects.create(first_name="Related", org=org_a))
    Account.objects.create(
        name="Hidden", org=org_b, source="META", number_of_employees=12
    )
    Account.objects.create(
        name="Other", org=org_a, source="GOOGLE", number_of_employees=1
    )
    response = admin_client.get(
        "/api/accounts/",
        {
            "source": "META",
            "number_of_employees__gte": 10,
            "search": "Jobs",
            "sort": sort,
            "assigned_to": str(admin_profile.pk),
            "limit": 1,
        },
    )
    assert response.status_code == 200, response.data
    rows = response.data["active_accounts"]
    assert rows["open_accounts_count"] == 1
    assert str(rows["open_accounts"][0]["id"]) == str(a.pk)
    assert rows["open_accounts"][0]["source_label"] == "Meta"


def test_company_numeric_order_before_pagination(admin_client, org_a):
    for name, employees in [("Ten", 10), ("Two", 2), ("Thirty", 30)]:
        Account.objects.create(name=name, org=org_a, number_of_employees=employees)
    response = admin_client.get(
        "/api/accounts/",
        {"sort": "number_of_employees", "direction": "asc", "limit": 1, "offset": 1},
    )
    assert response.data["active_accounts"]["open_accounts"][0]["name"] == "Ten"
    assert (
        admin_client.get("/api/accounts/", {"annual_revenue__gte": "NaN"}).status_code
        == 400
    )


def test_company_stage_moves_preserve_source_and_reset_age(admin_client, org_a):
    from datetime import timedelta
    from django.utils import timezone
    from contacts.choices import CONTACT_STAGES

    account = Account.objects.create(name="Stage test", org=org_a, source="META")
    assert account.stage == "LEAD"
    old = timezone.now() - timedelta(days=5)
    Account.objects.filter(pk=account.pk).update(stage_entered_at=old)
    url = f"/api/accounts/{account.pk}/"
    response = admin_client.patch(url, {"stage": "LEAD"}, format="json")
    assert response.status_code == 200, response.data
    account.refresh_from_db()
    assert account.stage_entered_at == old
    for stage, label in CONTACT_STAGES[1:]:
        response = admin_client.patch(url, {"stage": stage}, format="json")
        assert response.status_code == 200, response.data
        account.refresh_from_db()
        assert account.stage == stage
        assert account.stage_entered_at > old
        assert account.source == "META"
        page = admin_client.get("/api/accounts/", {"stage": stage}).data[
            "active_accounts"
        ]
        assert page["open_accounts_count"] == 1
        assert page["open_accounts"][0]["stage_label"] == label
    assert admin_client.patch(url, {"stage": "BAD"}, format="json").status_code == 400
    assert (
        admin_client.get("/api/accounts/", {"stage": "LEAD"}).data["active_accounts"][
            "open_accounts_count"
        ]
        == 0
    )


def test_company_property_filters(admin_client, org_a):
    contact = Contact.objects.create(first_name="Linked", org=org_a)
    company = Account.objects.create(
        name="Contractor",
        org=org_a,
        industry="HOME IMPROVEMENT",
        currency="USD",
        pages=[{"name": "Projects", "url": "https://example.com/projects"}],
    )
    company.contacts.add(contact)
    Account.objects.create(
        name="Other", org=org_a, industry="HOME IMPROVEMENT", currency="USD"
    )
    params = {
        "contacts": str(contact.pk),
        "industry": "HOME IMPROVEMENT",
        "currency": "USD",
        "pages": "projects",
    }
    response = admin_client.get("/api/accounts/", params)
    assert response.status_code == 200, response.data
    assert response.data["active_accounts"]["open_accounts_count"] == 1
    assert str(response.data["active_accounts"]["open_accounts"][0]["id"]) == str(
        company.pk
    )
    params["pages"] = "missing-page"
    assert (
        admin_client.get("/api/accounts/", params).data["active_accounts"][
            "open_accounts_count"
        ]
        == 0
    )
