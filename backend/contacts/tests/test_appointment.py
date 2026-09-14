from datetime import datetime, timezone

import pytest

from common.models import Activity
from contacts.models import Contact

pytestmark = pytest.mark.django_db


def test_appointment_create_update_clear(admin_client):
    response = admin_client.post(
        "/api/contacts/",
        {
            "name": "Appointment test",
            "phone": "3055550190",
            "source": "META",
            "stage": "LEAD",
            "appointment_at": "2026-10-01T10:30:00-04:00",
        },
        format="json",
    )
    assert response.status_code == 200, response.data
    contact = Contact.objects.get(first_name="Appointment test")
    assert contact.appointment_at == datetime(2026, 10, 1, 14, 30, tzinfo=timezone.utc)
    url = f"/api/contacts/{contact.pk}/"
    assert admin_client.get(url).data["contact_obj"]["appointment_at"]
    response = admin_client.patch(
        url, {"appointment_at": "2026-10-02T15:00:00Z"}, format="json"
    )
    assert response.status_code == 200, response.data
    history = Activity.objects.filter(entity_id=contact.pk, action="UPDATE").latest(
        "created_at"
    )
    assert "appointment_at" in history.metadata["changes"]
    assert history.user is not None
    response = admin_client.patch(url, {"city": "Miami"}, format="json")
    assert response.status_code == 200
    contact.refresh_from_db()
    assert contact.appointment_at == datetime(2026, 10, 2, 15, tzinfo=timezone.utc)
    response = admin_client.patch(url, {"appointment_at": None}, format="json")
    assert response.status_code == 200
    contact.refresh_from_db()
    assert contact.appointment_at is None


def test_invalid_appointment_does_not_save(admin_client, org_a):
    contact = Contact.objects.create(first_name="Invalid date", org=org_a)
    response = admin_client.patch(
        f"/api/contacts/{contact.pk}/", {"appointment_at": "not-a-date"}, format="json"
    )
    assert response.status_code == 400
    contact.refresh_from_db()
    assert contact.appointment_at is None
