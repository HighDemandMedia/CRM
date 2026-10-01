from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import patch

import pytest
from django.db import connection
from django.utils import timezone

from common.models import (
    CRMRole,
    GoogleCalendarEvent,
    GoogleCalendarMirror,
    GoogleConnection,
    Notification,
    ReminderDelivery,
    SalesAppointment,
)
from common.reminders import deliver_org_reminders
from common.tasks import send_due_reminders
from common.testing import rls_org
from tasks.models import Task

pytestmark = pytest.mark.django_db
NOW = datetime(2026, 10, 2, 2, 0, tzinfo=dt_timezone.utc)


def task(org, user, **kwargs):
    return Task.objects.create(org=org, created_by=user, title="Follow up", **kwargs)


def event(org, profile, **kwargs):
    return SalesAppointment.objects.create(
        org=org,
        created_by=profile.user,
        host=profile,
        title="Meeting",
        starts_at=kwargs.pop("starts_at", NOW + timedelta(minutes=15)),
        ends_at=NOW + timedelta(hours=1),
        **kwargs,
    )


def test_task_reminder_date_timezone_and_assignees(
    org_a, admin_user, admin_profile, user_profile
):
    org_a.timezone = "America/New_York"  # Still Oct 1 locally.
    due = NOW.date()
    t = task(org_a, admin_user, due_date=due, reminder_days=1)
    t.assigned_to.add(user_profile)
    task(org_a, admin_user, due_date=due, reminder_days=0)  # Not until tomorrow.
    task(org_a, admin_user, due_date=due, reminder_days=None)
    task(org_a, admin_user, due_date=due, reminder_days=1, status="Completed")
    task(org_a, admin_user, due_date=due - timedelta(days=3), reminder_days=1)
    deliver_org_reminders(org_a, NOW)
    n = Notification.objects.get()
    assert n.recipient == user_profile
    assert n.verb == "task.reminder"
    assert n.link == f"/tasks/{t.pk}"
    assert n.data["due_date"] == "2026-10-02"


def test_receipt_survives_read_delete_and_reschedule(org_a, admin_user, admin_profile):
    t = task(org_a, admin_user, due_date=NOW.date(), reminder_days=0)
    deliver_org_reminders(org_a, NOW)
    Notification.objects.update(read_at=NOW)
    deliver_org_reminders(org_a, NOW)
    assert Notification.objects.count() == 1
    Notification.objects.all().delete()
    deliver_org_reminders(org_a, NOW)
    assert Notification.objects.count() == 0
    assert ReminderDelivery.objects.count() == 1
    t.due_date += timedelta(days=1)
    t.save()
    deliver_org_reminders(org_a, NOW + timedelta(days=1))
    assert Notification.objects.count() == 1
    assert ReminderDelivery.objects.count() == 2


def test_notification_failure_rolls_back_receipt(org_a, admin_user, admin_profile):
    task(org_a, admin_user, due_date=NOW.date(), reminder_days=0)
    with (
        patch("common.reminders.notifications.create", side_effect=RuntimeError),
        pytest.raises(RuntimeError),
    ):
        deliver_org_reminders(org_a, NOW)
    assert not ReminderDelivery.objects.exists()
    deliver_org_reminders(org_a, NOW)
    assert Notification.objects.count() == 1


def test_calendar_window_recipients_cancellation_and_reschedule(
    org_a, admin_profile, user_profile
):
    meeting = event(org_a, admin_profile)
    meeting.attendee_users.add(admin_profile, user_profile)
    event(org_a, admin_profile, starts_at=NOW + timedelta(minutes=16))
    event(org_a, admin_profile, starts_at=NOW - timedelta(minutes=1))
    event(org_a, admin_profile, cancelled_at=NOW)
    deliver_org_reminders(org_a, NOW)
    assert set(Notification.objects.values_list("recipient_id", flat=True)) == {
        admin_profile.pk,
        user_profile.pk,
    }
    assert {n.link for n in Notification.objects.all()} == {"/calendar?date=2026-10-02"}
    deliver_org_reminders(org_a, NOW + timedelta(seconds=30))
    assert Notification.objects.count() == 2
    meeting.starts_at += timedelta(minutes=20)
    meeting.save()
    deliver_org_reminders(org_a, NOW + timedelta(minutes=21))
    assert Notification.objects.filter(entity_id=meeting.pk).count() == 4


@pytest.mark.parametrize(
    "field", ["notify_in_app", "is_active", "user_active", "removed_at"]
)
def test_inactive_or_opted_out_never_notified(org_a, admin_user, admin_profile, field):
    if field == "user_active":
        admin_user.is_active = False
        admin_user.save()
    else:
        setattr(admin_profile, field, NOW if field == "removed_at" else False)
        admin_profile.save()
    task(org_a, admin_user, due_date=NOW.date(), reminder_days=0)
    event(org_a, admin_profile)
    deliver_org_reminders(org_a, NOW)
    assert not Notification.objects.exists()
    assert not ReminderDelivery.objects.exists()


def test_permissions_and_cross_org_recipients(
    org_a, org_b, admin_user, admin_profile, user_profile, profile_b
):
    role = CRMRole.objects.create(
        org=org_a,
        name="No reminders access",
        rules={"tasks": {"view": "none"}, "calendar": {"view": "none"}},
    )
    user_profile.access_role = role
    user_profile.save()
    t = task(org_a, admin_user, due_date=NOW.date(), reminder_days=0)
    t.assigned_to.add(user_profile, profile_b)
    meeting = event(org_a, admin_profile)
    meeting.attendee_users.add(user_profile, profile_b)
    with rls_org(org_b):
        task(org_b, admin_user, due_date=NOW.date(), reminder_days=0)
    deliver_org_reminders(org_a, NOW)
    assert list(Notification.objects.values_list("recipient_id", flat=True)) == [
        admin_profile.pk
    ]
    assert Notification.objects.get().verb == "calendar.reminder"


def test_google_private_events_and_mirror_dedupe(org_a, admin_profile, user_profile):
    conn = GoogleConnection.objects.create(
        org=org_a, profile=admin_profile, service="calendar", status="connected"
    )
    meeting = event(org_a, admin_profile)
    GoogleCalendarMirror.objects.create(
        org=org_a, connection=conn, appointment=meeting, external_id="mirror"
    )
    for external_id, all_day in [
        ("native", False),
        ("mirror", False),
        ("all-day", True),
    ]:
        GoogleCalendarEvent.objects.create(
            org=org_a,
            connection=conn,
            external_id=external_id,
            title=external_id,
            starts_at=NOW + timedelta(minutes=5),
            ends_at=NOW + timedelta(hours=1),
            all_day=all_day,
        )
    deliver_org_reminders(org_a, NOW)
    assert set(Notification.objects.values_list("entity_name", flat=True)) == {
        "Meeting",
        "native",
    }
    assert not Notification.objects.filter(recipient=user_profile).exists()
    conn.status = "disconnected"
    conn.save()
    Notification.objects.all().delete()
    ReminderDelivery.objects.all().delete()
    meeting.cancelled_at = NOW
    meeting.save()
    deliver_org_reminders(org_a, NOW)
    assert not Notification.objects.exists()


def test_scheduler_restores_context_and_continues_after_failure(org_a, org_b):
    old_tz = timezone.get_current_timezone()
    with (
        patch(
            "common.reminders.deliver_org_reminders", side_effect=[RuntimeError, None]
        ) as scan,
        patch("common.tasks.set_rls_context") as set_context,
        patch("common.tasks.clear_rls_context") as clear,
    ):
        send_due_reminders()
    assert scan.call_count == 2
    assert set_context.call_count == clear.call_count == 2
    assert timezone.get_current_timezone() == old_tz


def test_beat_registers_reminder_scan():
    from crm.celery import app

    assert (
        app.conf.beat_schedule["send-due-reminders"]["task"]
        == "common.tasks.send_due_reminders"
    )


def test_receipt_table_has_rls_on_postgres():
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL RLS")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname='reminder_delivery'"
        )
        assert cursor.fetchone() == (True, True)
