import pytest

from common.custom_fields import _coerce_value, validate_payload
from common.models import CustomFieldDefinition


@pytest.mark.parametrize(
    "kind,raw,expected",
    [
        ("email", " person@example.com ", "person@example.com"),
        ("url", "example.com/path", "https://example.com/path"),
        ("phone", "+1 (202) 555-0123", "+12025550123"),
        ("integer", "12", 12),
        ("percentage", "0", 0),
        ("percentage", "100", 100),
        ("money", "12345678901234.56", "12345678901234.56"),
        ("money", "0", "0.00"),
        ("time", "14:30", "14:30:00"),
        ("multi_select", ["a", "b", "a"], ["a", "b"]),
    ],
)
def test_new_type_normalization(kind, raw, expected):
    assert _coerce_value(kind, raw) == (expected, None)


@pytest.mark.parametrize(
    "kind,raw",
    [
        ("email", "bad"),
        ("url", "javascript:alert(1)"),
        ("phone", "abc1234567"),
        ("phone", "++12345678"),
        ("integer", "1.2"),
        ("integer", True),
        ("percentage", 101),
        ("percentage", -1),
        ("money", "1.001"),
        ("number", "NaN"),
        ("money", "Infinity"),
        ("time", "25:30"),
        ("time", "12:00+01:00"),
        ("multi_select", "a"),
        ("multi_select", [1]),
    ],
)
def test_new_type_rejects_invalid_value(kind, raw):
    assert _coerce_value(kind, raw)[1]


@pytest.mark.django_db
def test_multiple_selection_required_and_option_validation(org_a):
    CustomFieldDefinition.objects.create(
        org=org_a,
        target_model="Contact",
        key="areas",
        label="Areas",
        field_type="multi_select",
        options=[{"value": "a", "label": "Area A"}],
        is_required=True,
    )
    assert validate_payload("Contact", {"areas": ["a"]}, org_a) == (
        {"areas": ["a"]},
        {},
    )
    assert "areas" in validate_payload("Contact", {"areas": ["wrong"]}, org_a)[1]
    # Core records enforce required properties at the configured pipeline stage.
    assert validate_payload("Contact", {"areas": []}, org_a) == ({}, {})


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind",
    ["email", "phone", "url", "integer", "percentage", "money", "time", "multi_select"],
)
def test_create_new_type_definition(admin_client, kind):
    body = {
        "target_model": "Contact",
        "key": f"custom_{kind}",
        "label": kind,
        "field_type": kind,
    }
    if kind == "multi_select":
        body["options"] = [{"value": "a", "label": "Area A"}]
    result = admin_client.post("/api/custom-fields/", body, format="json")
    assert result.status_code == 201, result.data
    assert result.data["field_type"] == kind
