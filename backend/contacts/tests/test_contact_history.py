from datetime import timedelta

import pytest
from django.utils import timezone

from common.models import Activity, Comment
from contacts.models import Contact

pytestmark = pytest.mark.django_db


def test_creation_stage_clock_actor_and_changes(admin_client, admin_user):
    response = admin_client.post(
        "/api/contacts/",
        {
            "name": "History test",
            "phone": "3055550199",
            "source": "META",
            "stage": "LEAD",
            "created_by": "fake",
            "stage_entered_at": "2000-01-01T00:00:00Z",
        },
        format="json",
    )
    assert response.status_code == 200, response.data
    contact = Contact.objects.get(first_name="History test")
    assert contact.created_by_id == admin_user.id
    assert contact.stage_entered_at >= timezone.now() - timedelta(minutes=1)
    assert not Activity.objects.filter(entity_id=contact.id, action="CREATE").exists()
    entered = contact.stage_entered_at
    response = admin_client.patch(
        f"/api/contacts/{contact.id}/", {"city": "Miami"}, format="json"
    )
    assert response.status_code == 200, response.data
    contact.refresh_from_db()
    assert contact.stage_entered_at == entered
    update = Activity.objects.filter(entity_id=contact.id, action="UPDATE").latest(
        "created_at"
    )
    assert update.metadata["changes"]["city"]["after"] == "Miami"
    assert update.user.user_id == admin_user.id
    response = admin_client.patch(
        f"/api/contacts/{contact.id}/", {"stage": "QUALIFIED"}, format="json"
    )
    assert response.status_code == 200
    contact.refresh_from_db()
    assert contact.stage_entered_at > entered
    update = Activity.objects.filter(entity_id=contact.id, action="UPDATE").latest(
        "created_at"
    )
    assert update.metadata["changes"]["stage"]["before"] == "LEAD"
    assert update.metadata["changes"]["stage"]["after"] == "QUALIFIED"
    history = admin_client.get(f"/api/contacts/{contact.id}/").data["history"]
    assert all(row["actor"] == admin_user.email for row in history)
    assert all(row["action"] in ("UPDATE", "ASSIGN") for row in history)


def test_legacy_clock_not_invented_and_noop_not_logged(admin_client, org_a):
    contact = Contact.objects.create(first_name="Legacy", org=org_a, stage="LEAD")
    Contact.objects.filter(pk=contact.id).update(stage_entered_at=None)
    before = Activity.objects.filter(entity_id=contact.id, action="UPDATE").count()
    response = admin_client.patch(
        f"/api/contacts/{contact.id}/", {"stage": "LEAD"}, format="json"
    )
    assert response.status_code == 200
    contact.refresh_from_db()
    assert contact.stage_entered_at is None
    assert (
        Activity.objects.filter(entity_id=contact.id, action="UPDATE").count() == before
    )


def test_owner_notes_and_cross_org_history(
    admin_client, org_b_client, org_a, admin_user
):
    contact = Contact.objects.create(
        first_name="Notes", org=org_a, created_by=admin_user
    )
    profile = admin_user.profiles.get(org=org_a)
    response = admin_client.patch(
        f"/api/contacts/{contact.id}/",
        {"assigned_to": [str(profile.pk)]},
        format="json",
    )
    assert response.status_code == 200, response.data
    assert Activity.objects.filter(
        entity_id=contact.id, action="ASSIGN", user=profile
    ).exists()
    response = admin_client.post(
        f"/api/contacts/{contact.id}/", {"comment": "Called customer"}, format="json"
    )
    assert response.status_code == 200, response.data
    assert not Activity.objects.filter(
        entity_id=contact.id, description="Note added", user=profile
    ).exists()
    note = Comment.objects.get(object_id=contact.pk)
    note.comment = "Revised note"
    note.save()
    note.delete()
    assert not Activity.objects.filter(
        entity_id=contact.id, description="Note updated"
    ).exists()
    assert not Activity.objects.filter(
        entity_id=contact.id, description="Note deleted"
    ).exists()
    assert org_b_client.get(f"/api/contacts/{contact.id}/").status_code == 404


def test_failed_audit_rolls_back_contact_creation(org_a):
    from unittest.mock import patch

    with patch(
        "contacts.signals.record", side_effect=RuntimeError("audit unavailable")
    ):
        with pytest.raises(RuntimeError):
            Contact.objects.create(
                first_name="Should roll back", org=org_a, stage="LEAD"
            )
    assert not Contact.objects.filter(first_name="Should roll back").exists()
