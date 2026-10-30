from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core import mail
from django.utils import timezone

from common.models import Notification
from common.notification_delivery import delivery_batch
from common.notification_emails import deliver_notification_emails
from common.notification_preferences import channels_for
from common.notifications import create
from common.testing import rls_org

pytestmark = pytest.mark.django_db


def configure(profile, **channels):
    profile.notification_preferences = {
        "task.reminder": {
            "popup": False,
            "browser": False,
            "bell": False,
            "email": False,
            **channels,
        }
    }
    profile.save(update_fields=["notification_preferences"])


def test_defaults_preserve_existing_choices(user_profile):
    assert channels_for(user_profile, "task.reminder") == {
        "popup": True,
        "browser": False,
        "bell": True,
        "email": False,
    }
    user_profile.notify_in_app = False
    assert not any(channels_for(user_profile, "task.reminder").values())
    assert channels_for(user_profile, "webform.submitted")["email"]


def test_own_profile_matrix_is_validated_and_persisted(
    user_client, user_profile, admin_profile
):
    configure(user_profile, popup=True)
    matrix = user_profile.notification_preferences
    response = user_client.patch(
        "/api/profile/", {"notification_preferences": matrix}, format="json"
    )
    assert response.status_code == 200
    result = user_client.get("/api/profile/").data["user_obj"]["notification_settings"]
    assert result["values"]["task.reminder"] == matrix["task.reminder"]
    admin_profile.refresh_from_db()
    assert admin_profile.notification_preferences == {}
    for bad in (
        [],
        {"bogus": {}},
        {"task.reminder": {"sms": True}},
        {"task.reminder": {"email": "false"}},
        {"task.reminder": {"email": 1}},
    ):
        assert (
            user_client.patch(
                "/api/profile/", {"notification_preferences": bad}, format="json"
            ).status_code
            == 400
        )
    user_profile.refresh_from_db()
    assert user_profile.notification_preferences == matrix


def test_popup_browser_and_email_do_not_require_bell(user_profile, user_client):
    configure(user_profile, popup=True, browser=True, email=True)
    user_profile.notify_in_app = False
    user_profile.save(update_fields=["notify_in_app"])
    row = create(user_profile, "task.reminder", entity_name="Test")
    assert row.email_pending
    result = user_client.get("/api/notifications/?delivery=true").json()
    assert result["count"] == result["unread_count"] == 0
    assert result["results"] == []
    assert [item["id"] for item in result["deliveries"]] == [str(row.pk)]
    assert result["deliveries"][0]["channels"]["browser"] is True
    assert user_client.post(f"/api/notifications/{row.pk}/read/").status_code == 404


def test_all_off_skips_and_webform_uses_existing_email_outbox(user_profile):
    configure(user_profile)
    assert create(user_profile, "task.reminder") is None
    row = create(user_profile, "webform.submitted")
    assert row.channels["email"] and not row.email_pending


def test_delivery_cursor_is_scoped_and_bounded(user_profile, admin_profile, org_a):
    configure(user_profile, browser=True)
    with rls_org(org_a):
        rows = [create(user_profile, "task.reminder") for _ in range(101)]
        foreign = create(admin_profile, "task.reminder")
        batch = delivery_batch(user_profile)
        assert len(batch["deliveries"]) == 100 and batch["delivery_more"]
        next_batch = delivery_batch(user_profile, batch["delivery_cursor"])
        assert len(next_batch["deliveries"]) == 1 and not next_batch["delivery_more"]
        assert str(foreign.pk) not in {item["id"] for item in batch["deliveries"]}
        assert not delivery_batch(user_profile, next_batch["delivery_cursor"])[
            "deliveries"
        ]
        # A cursor from another user cannot expose their notifications.
        other = delivery_batch(admin_profile, batch["delivery_cursor"])
        assert {item["id"] for item in other["deliveries"]} == {str(foreign.pk)}
        assert len(delivery_batch(user_profile, "forged")["deliveries"]) == 100
        configure(user_profile)
        assert not delivery_batch(user_profile)["deliveries"]
        assert (
            Notification.objects.filter(pk__in=[row.pk for row in rows]).count() == 101
        )


def test_email_is_branded_private_idempotent_and_preference_aware(user_profile, org_a):
    configure(user_profile, email=True)
    row = create(
        user_profile,
        "task.reminder",
        entity_name="PRIVATE NAME",
        data={"comment_excerpt": "SECRET COMMENT"},
        link="https://evil.test/",
    )
    deliver_notification_emails(org_a)
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user_profile.user.email]
    message = mail.outbox[0].body + mail.outbox[0].alternatives[0].content
    assert "High Demand Media" in message
    assert (
        "PRIVATE NAME" not in message
        and "SECRET COMMENT" not in message
        and "evil.test" not in message
    )
    row.refresh_from_db()
    assert row.email_sent_at and not row.email_pending
    deliver_notification_emails(org_a)
    assert len(mail.outbox) == 1
    skipped = create(user_profile, "task.reminder")
    configure(user_profile)
    deliver_notification_emails(org_a)
    skipped.refresh_from_db()
    assert not skipped.email_pending and not skipped.email_sent_at
    assert len(mail.outbox) == 1


def test_email_failure_waits_before_retry(user_profile, org_a):
    configure(user_profile, email=True)
    row = create(user_profile, "task.reminder")
    with patch(
        "common.tasks.send_email", side_effect=RuntimeError("provider unavailable")
    ) as send:
        deliver_notification_emails(org_a)
        deliver_notification_emails(org_a)
        assert send.call_count == 1
    row.refresh_from_db()
    assert row.email_pending and row.email_attempts == 1
    Notification.objects.filter(pk=row.pk).update(
        email_attempted_at=timezone.now() - timedelta(minutes=6)
    )
    deliver_notification_emails(org_a)
    row.refresh_from_db()
    assert row.email_sent_at and row.email_attempts == 2


def test_removed_user_and_closed_organization_receive_no_email(user_profile, org_a):
    configure(user_profile, email=True)
    row = create(user_profile, "task.reminder")
    user_profile.removed_at = timezone.now()
    user_profile.save(update_fields=["removed_at"])
    deliver_notification_emails(org_a)
    assert not mail.outbox
    row.refresh_from_db()
    assert not row.email_pending
    user_profile.removed_at = None
    user_profile.save(update_fields=["removed_at"])
    create(user_profile, "task.reminder")
    org_a.closing_at = timezone.now()
    org_a.save(update_fields=["closing_at"])
    deliver_notification_emails(org_a)
    assert not mail.outbox


def test_delivery_receipts_expire_without_purging_unread_bell(user_profile, org_a):
    from common.tasks import purge_read_notifications

    configure(user_profile, email=True)
    hidden = create(user_profile, "task.reminder")
    configure(user_profile, bell=True)
    visible = create(user_profile, "task.reminder")
    Notification.objects.filter(pk__in=[hidden.pk, visible.pk]).update(
        created_at=timezone.now() - timedelta(days=100)
    )
    purge_read_notifications()
    with rls_org(org_a):
        assert not Notification.objects.filter(pk=hidden.pk).exists()
        assert Notification.objects.filter(pk=visible.pk).exists()
