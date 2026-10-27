import pytest

from common.custom_fields import _coerce_value
from common.phone_numbers import phone_e164, phone_match_key
from common.record_validation import clean_record_values


@pytest.mark.parametrize(
    "raw,region,expected",
    [
        ("(202) 555-0123", "US", "+12025550123"),
        ("+1 202 555 0123", "US", "+12025550123"),
        ("099 123 456", "UY", "+59899123456"),
        ("+598 99 123 456", "US", "+59899123456"),
        ("020 7946 0018", "GB", "+442079460018"),
        ("+39 02 3661 8300", "US", "+390236618300"),
    ],
)
def test_phone_normalization(raw, region, expected):
    assert phone_e164(raw, region) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "+999123456789",
        "+1202",
        "0123456789",
        "+12025550123 ext 12",
        "Call +12025550123",
        "1+2025550123",
        "+1234567890123456",
    ],
)
def test_invalid_phone(raw):
    with pytest.raises(ValueError):
        phone_e164(raw)


def test_duplicates_preserve_country_and_legacy_us():
    assert phone_match_key("2025550123") == phone_match_key("+1 (202) 555-0123")
    assert phone_match_key("+442025550123") != phone_match_key("+12025550123")
    assert phone_match_key("+598 99 123 456") == "59899123456"


def test_system_and_custom_fields_store_e164():
    assert (
        clean_record_values({"phone": "(202) 555-0123"}, "Contact")["phone"]
        == "+12025550123"
    )
    assert _coerce_value("phone", "+598 99 123 456") == ("+59899123456", None)


@pytest.mark.django_db
@pytest.mark.parametrize("route", ["contacts", "accounts", "opportunities"])
def test_record_api_normalizes_and_rejects_invalid(admin_client, route):
    identity = (
        {"email": "phone-qa@example.com"}
        if route == "contacts"
        else {"website": "https://phone-qa.example.com"}
        if route == "accounts"
        else {}
    )
    response = admin_client.post(
        f"/api/{route}/",
        {"name": "International phone QA", "phone": "+598 99 123 456", **identity},
        format="json",
    )
    assert response.status_code in (200, 201), response.data
    from accounts.models import Account
    from contacts.models import Contact
    from opportunity.models import Opportunity

    model = {"contacts": Contact, "accounts": Account, "opportunities": Opportunity}[
        route
    ]
    assert model.objects.filter(phone="+59899123456").exists()
    bad = admin_client.post(
        f"/api/{route}/",
        {"name": "Bad phone QA", "phone": "+999123456789"},
        format="json",
    )
    assert bad.status_code == 400


@pytest.mark.django_db
def test_phone_index_migration_visits_each_tenant_and_restores_context(org_a, org_b):
    from importlib import import_module
    from types import SimpleNamespace

    from django.apps import apps
    from django.db import connection

    from common.rls.context import org_context
    from contacts.models import Contact

    rows = []
    for org, phone, expected in (
        (org_a, "2025550123", "12025550123"),
        (org_b, "+598 99 123 456", "59899123456"),
    ):
        with org_context(org.pk):
            row = Contact.objects.create(org=org, first_name="Legacy", phone=phone)
            Contact.objects.filter(pk=row.pk).update(phone_match_key="old-key")
            rows.append((org, row.pk, phone, expected))
    with org_context(org_a.pk):
        import_module("contacts.migrations.0023_international_phone_keys").update_keys(
            apps, SimpleNamespace(connection=connection)
        )
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_setting('app.current_org', true)")
                assert cursor.fetchone()[0] == str(org_a.pk)
    for org, pk, phone, expected in rows:
        with org_context(org.pk):
            row = Contact.objects.get(pk=pk)
            assert row.phone_match_key == expected
            assert row.phone == phone


@pytest.mark.postgres_only
@pytest.mark.django_db
def test_phone_index_migration_with_enforced_rls(org_a, org_b):
    from django.db import connection

    assert connection.vendor == "postgresql"
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
        )
        assert cursor.fetchone() == (False, False)
    test_phone_index_migration_visits_each_tenant_and_restores_context(org_a, org_b)
