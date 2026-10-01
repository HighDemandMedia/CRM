from datetime import datetime, timezone

import pytest
from rest_framework.exceptions import ValidationError

from accounts.models import Account
from common.pipeline_settings import rule_properties, validate_entry
from contacts.models import Contact

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "route,model,fields",
    [
        ("contacts", Contact, {"first_name": "Calendar contact"}),
        ("accounts", Account, {"name": "Calendar company"}),
    ],
)
@pytest.mark.parametrize("value", ["2026-10-02T15:00:00Z", None, "", "not-a-date"])
def test_appointment_cannot_be_set_or_cleared_in_record_api(
    admin_client, org_a, route, model, fields, value
):
    before = datetime(2026, 10, 1, 14, 30, tzinfo=timezone.utc)
    record = model.objects.create(org=org_a, appointment_at=before, **fields)
    for method in ("patch", "put"):
        response = getattr(admin_client, method)(
            f"/api/{route}/{record.pk}/",
            {"name": "Attempted edit", "appointment_at": value},
            format="json",
        )
        assert response.status_code == 400, response.data
        assert "Calendar" in str(response.data)
        record.refresh_from_db()
        assert record.appointment_at == before
    response = admin_client.post(
        f"/api/{route}/",
        {"name": "Attempted creation", "appointment_at": value},
        format="json",
    )
    assert response.status_code == 400, response.data
    assert model.objects.count() == 1
    response = admin_client.patch(
        f"/api/{route}/{record.pk}/", {"city": "Miami"}, format="json"
    )
    assert response.status_code == 200, response.data
    record.refresh_from_db()
    assert record.appointment_at == before


def test_appointment_stage_rule_uses_calendar_value_not_raw_payload(org_a):
    org_a.pipeline_settings = {
        "Contact": [
            {
                "key": "QUALIFIED",
                "label": "Qualified",
                "order": 0,
                "required_fields": ["appointment_at"],
                "allowed_from": [],
            }
        ]
    }
    record = Contact.objects.create(org=org_a, first_name="Stage test", stage="LEAD")
    properties = rule_properties(org_a, "Contact")
    assert next(p for p in properties if p["key"] == "appointment_at")["is_read_only"]
    with pytest.raises(ValidationError) as error:
        validate_entry(
            org_a,
            "Contact",
            record,
            {"stage": "QUALIFIED"},
            {"appointment_at": "2026-10-02T15:00:00Z"},
        )
    assert (
        error.value.detail["stage_requirements"]["fields"][0]["key"] == "appointment_at"
    )
    record.appointment_at = datetime(2026, 10, 1, 14, 30, tzinfo=timezone.utc)
    validate_entry(org_a, "Contact", record, {"stage": "QUALIFIED"})
