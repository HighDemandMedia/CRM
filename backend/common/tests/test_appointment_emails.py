from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core import mail
from django.db import transaction
from django.utils import timezone

from common.appointment_emails import pending_ids, queue_appointment_emails
from common.models import AppointmentEmailDelivery, SalesAppointment
from common.tasks import send_appointment_email
from common.testing import restore_rls_context, rls_org
from contacts.models import Contact

pytestmark = pytest.mark.django_db


@pytest.fixture
def meeting(admin_client, admin_profile, user_profile, org_a, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.FRONTEND_URL = "https://crm.example.com"
    org_a.timezone = "America/New_York"
    org_a.save(update_fields=["timezone"])
    contact = Contact.objects.create(
        org=org_a,
        first_name="Cliente <Demo>",
        email="client@example.com",
        language="Spanish",
    )
    response = admin_client.post(
        "/api/sales-appointments/",
        {
            "title": "Review <script>alert(1)</script>",
            "host": str(admin_profile.pk),
            "users": [str(user_profile.pk)],
            "contacts": [str(contact.pk)],
            "internal_notes": "INTERNAL SECRET",
            "starts_at": "2026-11-10T15:00:00Z",
            "ends_at": "2026-11-10T16:00:00Z",
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    return SalesAppointment.objects.get(pk=response.data["id"])


def deliver_one(delivery_id, org_id):
    try:
        send_appointment_email(str(delivery_id), str(org_id))
    finally:
        restore_rls_context()


def deliver_all(meeting):
    for row in AppointmentEmailDelivery.objects.filter(appointment=meeting):
        deliver_one(row.pk, meeting.org_id)


def test_creation_is_private_branded_bilingual_and_idempotent(meeting):
    assert AppointmentEmailDelivery.objects.filter(appointment=meeting).count() == 3
    deliver_all(meeting)
    assert len(mail.outbox) == 3
    for message in mail.outbox:
        assert len(message.to) == 1 and not message.cc and not message.bcc
        html = message.alternatives[0].content
        assert "INTERNAL SECRET" not in message.body + html
        assert "<script>" not in html and "&lt;script&gt;" in html
        assert "linear-gradient(135deg,#AC0F0B,#CA4618)" in html
        assert "background-color:#292D30" in html
        if message.to == ["client@example.com"]:
            assert message.subject == "Cita confirmada · HDM CRM"
            assert "10/11/2026 · 10:00" in message.body
            assert "America/New_York" in message.body
            assert "https://crm.example.com" not in message.body + html
            assert '<html lang="es"' in html
        else:
            assert "https://crm.example.com/calendar" in html
    deliver_all(meeting)
    assert len(mail.outbox) == 3


def test_reschedule_cancel_and_noop_updates(admin_client, meeting):
    deliver_all(meeting)
    path = f"/api/sales-appointments/{meeting.pk}/"
    body = {
        "operation": "reschedule",
        "starts_at": "2026-11-11T15:00:00Z",
        "ends_at": "2026-11-11T16:00:00Z",
    }
    assert admin_client.patch(path, body, format="json").status_code == 200
    deliver_all(meeting)
    assert len(mail.outbox) == 6
    assert any("Cita reprogramada" in m.subject for m in mail.outbox)
    external = [m for m in mail.outbox if m.to == ["client@example.com"]][-1]
    assert "Inicio anterior: 10/11/2026" in external.body
    assert "Inicio: 11/11/2026" in external.body
    assert admin_client.patch(path, body, format="json").status_code == 200
    assert (
        admin_client.patch(
            path,
            {
                "operation": "details",
                "title": "Updated",
                "internal_notes": "Still private",
            },
            format="json",
        ).status_code
        == 200
    )
    assert AppointmentEmailDelivery.objects.count() == 6
    assert (
        admin_client.patch(path, {"operation": "cancel"}, format="json").status_code
        == 200
    )
    assert (
        admin_client.patch(path, {"operation": "cancel"}, format="json").status_code
        == 200
    )
    deliver_all(meeting)
    assert len(mail.outbox) == 9
    assert any(m.subject == "Cita cancelada · HDM CRM" for m in mail.outbox)


def test_superseded_notice_is_not_sent(admin_client, meeting):
    admin_client.patch(
        f"/api/sales-appointments/{meeting.pk}/", {"operation": "cancel"}, format="json"
    )
    deliver_all(meeting)
    assert len(mail.outbox) == 3
    assert all("cancel" in m.subject.lower() for m in mail.outbox)
    assert (
        AppointmentEmailDelivery.objects.filter(completed_at__isnull=True).count() == 0
    )


def test_scope_and_inactive_recipient_are_rechecked(meeting, org_b, user_profile):
    for row in AppointmentEmailDelivery.objects.all():
        deliver_one(row.pk, org_b.pk)
    assert not getattr(mail, "outbox", [])
    user_profile.is_active = False
    user_profile.save(update_fields=["is_active"])
    Contact.objects.filter(pk=meeting.contacts.first().pk).update(
        email="changed@example.com"
    )
    deliver_all(meeting)
    assert [m.to for m in mail.outbox] == [[meeting.host.user.email]]


def test_closed_organization_does_not_send(meeting):
    meeting.org.closing_at = timezone.now()
    meeting.org.save(update_fields=["closing_at"])
    deliver_all(meeting)
    assert not getattr(mail, "outbox", [])


@pytest.mark.parametrize("failure", [OSError("mail unavailable"), 0])
def test_failed_delivery_retries_only_pending_recipient(meeting, failure):
    row = AppointmentEmailDelivery.objects.get(
        appointment=meeting, contact__isnull=False
    )
    with patch(
        "common.appointment_emails.EmailMultiAlternatives.send",
        side_effect=failure if isinstance(failure, Exception) else None,
        return_value=0,
    ):
        deliver_one(row.pk, meeting.org_id)
    row.refresh_from_db()
    assert row.attempts == 1 and row.sent_at is None and row.claim_id is None
    assert row.next_attempt_at > timezone.now()
    deliver_all(meeting)
    assert len(mail.outbox) == 2
    AppointmentEmailDelivery.objects.filter(pk=row.pk).update(
        next_attempt_at=timezone.now()
    )
    deliver_all(meeting)
    assert len(mail.outbox) == 3
    assert [m.to for m in mail.outbox].count(["client@example.com"]) == 1


def test_claim_blocks_duplicate_workers_and_expires(meeting):
    row = AppointmentEmailDelivery.objects.first()
    AppointmentEmailDelivery.objects.filter(pk=row.pk).update(claimed_at=timezone.now())
    deliver_one(row.pk, meeting.org_id)
    assert not getattr(mail, "outbox", [])
    assert row.pk not in pending_ids(meeting.org_id)
    AppointmentEmailDelivery.objects.filter(pk=row.pk).update(
        claimed_at=timezone.now() - timedelta(minutes=6)
    )
    assert row.pk in pending_ids(meeting.org_id)
    deliver_one(row.pk, meeting.org_id)
    assert len(mail.outbox) == 1


def test_broker_outage_preserves_outbox_and_rollback_does_not_queue(
    meeting, django_capture_on_commit_callbacks
):
    AppointmentEmailDelivery.objects.all().delete()
    with patch(
        "common.tasks.send_appointment_email.delay",
        side_effect=OSError("broker unavailable"),
    ) as dispatch:
        with django_capture_on_commit_callbacks(execute=True):
            with transaction.atomic():
                queue_appointment_emails(meeting, "scheduled")
                assert not dispatch.called
        assert dispatch.call_count == 3
    assert len(pending_ids(meeting.org_id)) == 3
    AppointmentEmailDelivery.objects.all().delete()
    with patch("common.tasks.send_appointment_email.delay") as dispatch:
        with django_capture_on_commit_callbacks(execute=True):
            with pytest.raises(RuntimeError), transaction.atomic():
                queue_appointment_emails(meeting, "scheduled")
                raise RuntimeError("rollback")
        dispatch.assert_not_called()
    assert not AppointmentEmailDelivery.objects.exists()


def test_deduplicates_addresses_and_ignores_foreign_contacts(meeting, org_b):
    AppointmentEmailDelivery.objects.all().delete()
    duplicate = Contact.objects.create(
        org=meeting.org,
        first_name="Same mailbox",
        email=meeting.host.user.email.upper(),
    )
    with rls_org(org_b):
        foreign = Contact.objects.create(
            org=org_b, first_name="Other tenant", email="foreign@example.com"
        )
    invalid = Contact.objects.create(
        org=meeting.org, first_name="No email", email="bad"
    )
    meeting.contacts.add(duplicate, foreign, invalid)
    queue_appointment_emails(meeting, "scheduled")
    assert AppointmentEmailDelivery.objects.count() == 3
    assert not AppointmentEmailDelivery.objects.filter(
        email="foreign@example.com"
    ).exists()
    deliver_all(meeting)
    assert len(mail.outbox) == 3


def test_outbox_is_deleted_with_appointment_and_has_rls(meeting):
    from common.rls import ORG_SCOPED_TABLES

    assert "appointment_email_delivery" in ORG_SCOPED_TABLES
    meeting.delete()
    assert not AppointmentEmailDelivery.objects.exists()


def test_delivery_failure_does_not_log_provider_payload(meeting, caplog):
    row = AppointmentEmailDelivery.objects.first()
    with patch(
        "common.appointment_emails.EmailMultiAlternatives.send",
        side_effect=OSError("SECRET_PROVIDER_DATA recipient@example.com"),
    ):
        deliver_one(row.pk, meeting.org_id)
    assert "retry scheduled" in caplog.text
    assert "SECRET_PROVIDER_DATA" not in caplog.text
    assert "recipient@example.com" not in caplog.text


def test_end_time_change_sends_reschedule(admin_client, meeting):
    deliver_all(meeting)
    response = admin_client.patch(
        f"/api/sales-appointments/{meeting.pk}/",
        {
            "operation": "reschedule",
            "starts_at": meeting.starts_at.isoformat(),
            "ends_at": (meeting.ends_at + timedelta(minutes=30)).isoformat(),
        },
        format="json",
    )
    assert response.status_code == 200
    deliver_all(meeting)
    assert len(mail.outbox) == 6
    assert (
        "Previous end:" in mail.outbox[-1].body
        or "Fin anterior:" in mail.outbox[-1].body
    )


def test_retry_scheduler_only_enqueues_eligible_pending_rows(meeting):
    from common.tasks import retry_appointment_emails

    rows = list(AppointmentEmailDelivery.objects.all())
    AppointmentEmailDelivery.objects.filter(pk=rows[0].pk).update(
        completed_at=timezone.now()
    )
    AppointmentEmailDelivery.objects.filter(pk=rows[1].pk).update(
        next_attempt_at=timezone.now() + timedelta(hours=1)
    )
    try:
        with patch("common.appointment_emails.enqueue") as enqueue:
            retry_appointment_emails()
        enqueue.assert_called_once_with(rows[2].pk, meeting.org_id)
        meeting.org.closing_at = timezone.now()
        meeting.org.save(update_fields=["closing_at"])
        with patch("common.appointment_emails.enqueue") as enqueue:
            retry_appointment_emails()
        enqueue.assert_not_called()
    finally:
        restore_rls_context()


@pytest.mark.postgres_only
def test_postgres_enforces_outbox_isolation(meeting, org_b):
    from django.db import connection

    from common.tasks import set_rls_context

    if connection.vendor != "postgresql":
        pytest.skip("RLS requires PostgreSQL")
    with connection.cursor() as cursor:
        cursor.execute("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")
        assert cursor.fetchone() == (False,)
    try:
        set_rls_context(org_b.pk)
        assert not AppointmentEmailDelivery.objects.exists()
    finally:
        set_rls_context(meeting.org_id)
    assert AppointmentEmailDelivery.objects.count() == 3
