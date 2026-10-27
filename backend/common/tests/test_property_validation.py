"""Format checks apply to creation and partial updates on all active objects."""

import pytest

from common.custom_fields import _coerce_value
from common.models import CustomFieldDefinition
from common.property_catalog import target_model


@pytest.mark.parametrize(
    "kind,value",
    [
        ("phone", "123456789"),
        ("phone", "+999123456789"),
        ("phone", "0123456789"),
        ("phone", "+13055550190 ext 5"),
        ("phone", "abcdefghij"),
        ("phone", 3055550190),
        ("text", {"bad": "object"}),
        ("text", ["bad"]),
        ("text", "a\nb"),
        ("text", "x" * 256),
        ("textarea", "\x00"),
        ("textarea", "x" * 10001),
        ("email", "person@"),
        ("url", "ftp://example.com"),
        ("integer", 1.5),
        ("number", float("inf")),
        ("percentage", 101),
        ("money", "12.345"),
        ("date", "2026-02-30"),
        ("date", "20260101"),
        ("date", "2026-W01-1"),
        ("time", "123000"),
        ("time", "24:01"),
        ("dropdown", True),
    ],
)
def test_invalid_property_format(kind, value):
    assert _coerce_value(kind, value)[1]


@pytest.mark.parametrize(
    "kind,value,expected",
    [
        ("phone", "3055550190", "+13055550190"),
        ("phone", "305-555-0190", "+13055550190"),
        ("phone", "+598 99 123 456", "+59899123456"),
        ("phone", "+44 20 7946 0018", "+442079460018"),
        ("text", "  Acme 2 & Co.  ", "Acme 2 & Co."),
        ("textarea", "Line 1\nLine 2", "Line 1\nLine 2"),
        ("date", "2028-02-29", "2028-02-29"),
        ("checkbox", False, False),
        ("integer", 0, 0),
        ("phone", "", None),
    ],
)
def test_valid_property_format(kind, value, expected):
    assert _coerce_value(kind, value) == (expected, None)


TARGETS = [
    ("Contact", "contacts", "first_name"),
    ("Account", "accounts", "name"),
    ("Opportunity", "opportunities", "name"),
    ("Task", "tasks", "title"),
    ("Case", "cases", "name"),
]


@pytest.mark.django_db
@pytest.mark.parametrize("target,route,name_field", TARGETS)
@pytest.mark.parametrize(
    "kind,bad,good",
    [
        ("phone", "abc1234567", "+13055550190"),
        ("email", "not-an-email", "person@example.com"),
        ("url", "javascript:alert(1)", "https://example.com"),
        ("integer", "1.5", 2),
        ("percentage", 101, 50),
        ("money", "1.001", "1.00"),
        ("date", "2026-02-30", "2026-02-28"),
        ("time", "25:00", "14:30:00"),
    ],
)
def test_custom_formats_on_create_and_edit(
    admin_client, org_a, admin_profile, target, route, name_field, kind, bad, good
):
    CustomFieldDefinition.objects.create(
        org=org_a,
        target_model=target,
        key="format_test",
        label="Format",
        field_type=kind,
    )
    body = {
        name_field: "Format check",
        "assigned_to": str(admin_profile.pk)
        if target == "Case"
        else [str(admin_profile.pk)],
        "custom_fields": {"format_test": bad},
    }
    if target == "Contact":
        body.update(email="format-check@example.com", phone="+12025550123")
    elif target == "Account":
        body["website"] = "https://format-check.example.com"
    result = admin_client.post(f"/api/{route}/", body, format="json")
    assert result.status_code == 400, result.data
    assert "format_test" in str(result.data), result.data
    record = target_model(target).objects.create(
        org=org_a, **{name_field: "Existing format record"}
    )
    result = admin_client.patch(
        f"/api/{route}/{record.pk}/",
        {"custom_fields": {"format_test": bad}},
        format="json",
    )
    assert result.status_code == 400, result.data
    record.refresh_from_db()
    assert "format_test" not in record.custom_fields
    result = admin_client.patch(
        f"/api/{route}/{record.pk}/",
        {"custom_fields": {"format_test": good}},
        format="json",
    )
    assert result.status_code == 200, result.data
    record.refresh_from_db()
    assert record.custom_fields["format_test"] == good


@pytest.mark.django_db
@pytest.mark.parametrize(
    "route,field,value",
    [
        ("opportunities", "amount", "-1.00"),
        ("opportunities", "amount", "1.001"),
        ("accounts", "number_of_employees", "1.5"),
        ("accounts", "annual_revenue", "-1"),
        ("accounts", "website", "ftp://example.com"),
    ],
)
def test_system_field_validation_returns_400(admin_client, route, field, value):
    result = admin_client.post(
        f"/api/{route}/", {"name": "Format check", field: value}, format="json"
    )
    assert result.status_code == 400, result.data
    assert field in str(result.data), result.data


@pytest.mark.django_db
@pytest.mark.parametrize("target,route,name_field", TARGETS[:3])
@pytest.mark.parametrize(
    "phone",
    ["123456789", "+999123456789", "0123456789", "+13055550190 ext 5", "abc1234567"],
)
def test_system_phone_on_create_and_edit(
    admin_client, org_a, target, route, name_field, phone
):
    result = admin_client.post(
        f"/api/{route}/", {name_field: "Phone format", "phone": phone}, format="json"
    )
    assert result.status_code == 400, result.data
    assert "phone" in str(result.data)
    record = target_model(target).objects.create(
        org=org_a, **{name_field: "Phone format", "phone": "3055550190"}
    )
    result = admin_client.patch(
        f"/api/{route}/{record.pk}/", {"phone": phone}, format="json"
    )
    assert result.status_code == 400, result.data
    record.refresh_from_db()
    assert record.phone == "3055550190"
    result = admin_client.patch(
        f"/api/{route}/{record.pk}/", {"phone": "+598 99 123 456"}, format="json"
    )
    assert result.status_code == 200, result.data
    record.refresh_from_db()
    assert record.phone == "+59899123456"
