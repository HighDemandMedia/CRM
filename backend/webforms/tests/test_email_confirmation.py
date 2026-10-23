"""Opt-in visitor mail, private staff notices and their independent outboxes."""

from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core import mail
from django.core.cache import cache
from django.utils import timezone

from common.models import CustomFieldDefinition
from common.tasks import set_rls_context
from webforms.dynamic_serializer import build_serializer
from webforms.email_content import submission_rows
from webforms.models import WebForm, WebFormField, WebFormSubmission
from webforms.service import submit_form
from webforms.tasks import retry_pending_webform_emails, send_webform_submission_email

pytestmark = pytest.mark.django_db


@pytest.fixture
def form(org_a, admin_profile):
    form = WebForm.objects.create(
        org=org_a,
        name="Website enquiries",
        target_model="Contact",
        assign_to=admin_profile,
        is_published=True,
        allowed_origins=["https://example.com"],
    )
    for order, (key, label) in enumerate(
        [
            ("first_name", "Your name"),
            ("email", "Email address"),
            ("description", "Message"),
        ]
    ):
        WebFormField.objects.create(
            org=org_a,
            form=form,
            order=order,
            source="lead",
            lead_field=key,
            label=label,
            is_required=key in {"first_name", "email"},
        )
    cache.clear()
    return form


def enable(form, **settings):
    for key, value in {"send_confirmation_email": True, **settings}.items():
        setattr(form, key, value)
    form.save()


def submit(form, **kwargs):
    return submit_form(
        form,
        {
            "first_name": "Pat",
            "email": "pat@example.com",
            "description": "Private message",
        },
        **kwargs,
    )


def deliver(row):
    send_webform_submission_email(str(row.pk), str(row.org_id))
    set_rls_context(row.org_id)


def test_confirmation_is_off_by_default_and_never_backfills(form):
    old = submit(form)
    assert not old.confirmation_requested
    enable(form)
    mail.outbox.clear()
    deliver(old)
    assert [message.to for message in mail.outbox] == [[form.assign_to.user.email]]
    fresh = submit(form)
    deliver(fresh)
    assert mail.outbox[-1].to == ["pat@example.com"]


@pytest.mark.parametrize(
    "language,heading",
    [("en", "We've received your request"), ("es", "Recibimos tu solicitud")],
)
def test_confirmation_is_localized_private_and_idempotent(form, language, heading):
    enable(form, notify_email=False)
    row = submit(form, submission_language=language)
    mail.outbox.clear()
    deliver(row)
    deliver(row)
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ["pat@example.com"]
    assert heading in message.subject and form.org.name in message.body
    html = message.alternatives[0].content
    assert f'<html lang="{language}"' in html
    assert "High Demand Media" in html and "background-color:#292D30" in html
    for content in (message.body, html):
        for private in (
            "Private message",
            "pat@example.com",
            "Your name",
            form.name,
            "/contacts/",
            "/leads/",
        ):
            assert private not in content
    row.refresh_from_db()
    assert row.confirmation_completed_at and not row.confirmation_claim_id


def test_payload_email_is_used_not_changed_contact_email(form):
    enable(form, notify_email=False)
    row = submit(form)
    row.contact.email = "different@example.com"
    row.contact.save(update_fields=["email"])
    mail.outbox.clear()
    deliver(row)
    assert mail.outbox[0].to == ["pat@example.com"]


@pytest.mark.parametrize(
    "email", [None, "", "not-an-email", "a@example.com\nBcc: bad@example.com", 123]
)
def test_confirmation_revalidates_destination(form, email):
    enable(form, notify_email=False)
    row = submit(form)
    row.payload["email"] = email
    row.save(update_fields=["payload"])
    mail.outbox.clear()
    deliver(row)
    row.refresh_from_db()
    assert not mail.outbox and row.confirmation_completed_at


def test_disabling_confirmation_cancels_pending_without_later_replay(form):
    enable(form, notify_email=False)
    row = submit(form)
    form.send_confirmation_email = False
    form.save(update_fields=["send_confirmation_email"])
    mail.outbox.clear()
    deliver(row)
    enable(form)
    deliver(row)
    assert not mail.outbox


@pytest.mark.parametrize(
    "status", [WebFormSubmission.REJECTED_SPAM, WebFormSubmission.REJECTED_INVALID]
)
def test_rejections_cannot_send_confirmation(form, status):
    enable(form)
    row = submit(form, rejected=status)
    assert not row.confirmation_requested
    row.confirmation_requested = True
    row.save(update_fields=["confirmation_requested"])
    mail.outbox.clear()
    deliver(row)
    assert not mail.outbox


def test_wrong_tenant_cannot_deliver_confirmation(form, org_b):
    enable(form)
    row = submit(form)
    mail.outbox.clear()
    send_webform_submission_email(str(row.pk), str(org_b.pk))
    assert not mail.outbox


def test_confirmation_claim_blocks_overlapping_delivery_and_can_expire(form):
    enable(form, notify_email=False)
    row = submit(form)
    row.confirmation_claim_id = uuid4()
    row.confirmation_claimed_at = timezone.now()
    row.save(update_fields=["confirmation_claim_id", "confirmation_claimed_at"])
    mail.outbox.clear()
    deliver(row)
    assert not mail.outbox
    row.confirmation_claimed_at = timezone.now() - timedelta(minutes=6)
    row.save(update_fields=["confirmation_claimed_at"])
    deliver(row)
    assert len(mail.outbox) == 1


def test_worker_reentry_does_not_duplicate_confirmation(form):
    enable(form, notify_email=False)
    row = submit(form)
    with patch(
        "webforms.tasks.send_email", side_effect=lambda **_: deliver(row)
    ) as sender:
        deliver(row)
    assert sender.call_count == 1


def test_guest_failure_retries_without_repeating_staff_mail(form):
    enable(form)
    row = submit(form)
    with patch(
        "webforms.tasks.send_email", side_effect=[None, ConnectionError]
    ) as sender:
        with pytest.raises(ConnectionError):
            deliver(row)
        assert sender.call_count == 2
    set_rls_context(row.org_id)
    row.refresh_from_db()
    assert row.email_completed_at and not row.confirmation_claim_id
    with patch("webforms.tasks.send_email") as sender:
        deliver(row)
    assert sender.call_count == 1 and sender.call_args.kwargs["recipients"] == [
        "pat@example.com"
    ]


def test_staff_failure_does_not_prevent_confirmation(form):
    enable(form)
    row = submit(form)
    with patch(
        "webforms.tasks.send_email", side_effect=[ConnectionError, None]
    ) as sender:
        with pytest.raises(ConnectionError):
            deliver(row)
        assert sender.call_args_list[1].kwargs["recipients"] == ["pat@example.com"]
    set_rls_context(row.org_id)
    row.refresh_from_db()
    assert row.confirmation_completed_at and not row.email_completed_at
    with patch("webforms.tasks.send_email") as sender:
        deliver(row)
    assert sender.call_count == 1 and sender.call_args.kwargs["recipients"] == [
        form.assign_to.user.email
    ]


def test_scheduler_retries_guest_after_internal_completion(form):
    enable(form, notify_email=False)
    row = submit(form)
    row.email_completed_at = timezone.now()
    row.save(update_fields=["email_completed_at"])
    with patch("webforms.tasks.queue_notification") as enqueue:
        retry_pending_webform_emails()
    assert (row.pk, row.org_id) in [call.args for call in enqueue.call_args_list]


def test_request_retry_keeps_one_confirmation(form):
    enable(form, notify_email=False)
    request_id = uuid4()
    first = submit(form, request_id=request_id, submission_language="es")
    second = submit(form, request_id=request_id, submission_language="en")
    assert first.pk == second.pk and second.submission_language == "es"
    mail.outbox.clear()
    deliver(first)
    deliver(second)
    assert len(mail.outbox) == 1


@pytest.mark.parametrize("target", ["Contact", "Lead"])
def test_public_language_is_validated_and_never_written_to_record(
    form, unauthenticated_client, target
):
    enable(form, target_model=target)
    endpoint = f"/api/public/forms/{form.org_id}/{form.pk}/submit/"
    base = {"first_name": "Pat", "email": "pat@example.com"}
    for language, expected in [("fr", 400), ("es", 200)]:
        response = unauthenticated_client.post(
            endpoint,
            {**base, "submission_language": language},
            format="json",
            HTTP_ORIGIN="https://example.com",
        )
        assert response.status_code == expected, response.data
    row = form.submissions.get(status=WebFormSubmission.ACCEPTED)
    assert row.submission_language == "es" and row.confirmation_requested
    assert "submission_language" not in row.payload
    assert "submission_language" not in (row.contact or row.lead).custom_fields


def test_historical_custom_field_cannot_override_language_allowlist(form):
    field = CustomFieldDefinition.objects.create(
        org=form.org,
        target_model="Contact",
        key="submission_language",
        label="Legacy",
        field_type="text",
    )
    WebFormField.objects.create(
        org=form.org, form=form, source="custom", custom_field=field, label="Legacy"
    )
    serializer = build_serializer(form)(
        data={
            "first_name": "Pat",
            "email": "pat@example.com",
            "submission_language": "fr",
        }
    )
    assert not serializer.is_valid() and "submission_language" in serializer.errors
    serializer = build_serializer(form)(
        data={
            "first_name": "Pat",
            "email": "pat@example.com",
            "submission_language": "es",
        }
    )
    assert serializer.is_valid(), serializer.errors
    assert (
        serializer.custom_values() == {}
        and "submission_language" not in serializer.lead_values()
    )


def test_configuration_toggle_and_reserved_mapping(form, admin_client, user_client):
    endpoint = f"/api/webforms/{form.pk}/"
    assert (
        admin_client.put(
            endpoint, {"send_confirmation_email": True}, format="json"
        ).status_code
        == 200
    )
    form.refresh_from_db()
    assert form.send_confirmation_email
    assert (
        user_client.put(
            endpoint, {"send_confirmation_email": False}, format="json"
        ).status_code
        == 403
    )
    response = admin_client.put(
        endpoint,
        {
            "fields": [
                {
                    "source": "lead",
                    "lead_field": "email",
                    "label": "Email",
                    "external_name": "submission_language",
                }
            ]
        },
        format="json",
    )
    assert response.status_code == 400


def test_staff_notice_has_configured_labels_choices_linebreaks_and_plaintext(
    form, admin_profile
):
    admin_profile.user.ui_language = "es"
    admin_profile.user.save(update_fields=["ui_language"])
    field = CustomFieldDefinition.objects.create(
        org=form.org,
        target_model="Contact",
        key="interests",
        label="Interests",
        field_type="multi_select",
        options=[
            {"value": "crm", "label": "CRM access"},
            {"value": "ads", "label": "Advertising"},
        ],
    )
    WebFormField.objects.create(
        org=form.org,
        form=form,
        order=3,
        source="custom",
        custom_field=field,
        label="Selected services",
    )
    row = submit_form(
        form,
        {
            "first_name": "<script>Pat</script>",
            "email": "pat@example.com",
            "description": "Line one\nLine two",
        },
        custom_fields={"interests": ["crm", "ads"], "consent": False},
    )
    mail.outbox.clear()
    deliver(row)
    message = mail.outbox[0]
    html = message.alternatives[0].content
    assert "Nueva solicitud" in message.subject
    assert "Your name" in html and "first_name" not in html
    assert "Line one<br>Line two" in html
    assert "Selected services" in html and "CRM access, Advertising" in html
    assert (
        "custom_fields" not in html
        and "&lt;script&gt;" in html
        and "<script>" not in html
    )
    assert "Message: Line one\nLine two" in message.body
    assert "Consent: No" in message.body
    assert [row["label"] for row in submission_rows(row)][:3] == [
        "Your name",
        "Email address",
        "Message",
    ]


@pytest.mark.parametrize("internal_done", [False, True])
def test_closure_cancels_visitor_outbox_even_after_reactivation(
    form, admin_user, settings, internal_done
):
    from common.organization_lifecycle import change_lifecycle

    settings.CRM_ORG_CLOSURE_ENABLED = True
    admin_user.is_superuser = True
    admin_user.save(update_fields=["is_superuser"])
    enable(form)
    row = submit(form)
    if internal_done:
        row.email_completed_at = timezone.now()
        row.save(update_fields=["email_completed_at"])
    change_lifecycle(form.org_id, admin_user, "close")
    row.refresh_from_db()
    assert row.confirmation_completed_at and row.email_completed_at
    change_lifecycle(form.org_id, admin_user, "reactivate")
    with patch("webforms.tasks.queue_notification") as enqueue:
        retry_pending_webform_emails()
    assert not enqueue.called
    mail.outbox.clear()
    deliver(row)
    assert not mail.outbox


@pytest.mark.postgres_only
@pytest.mark.django_db(transaction=True)
def test_postgres_concurrent_workers_send_one_confirmation(form):
    from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
    from threading import Barrier, Event

    from django.db import close_old_connections, connection

    from common.tasks import clear_rls_context
    from webforms.tasks import _deliver_confirmation

    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locking")
    enable(form, notify_email=False)
    row = submit(form)
    start = Barrier(2)
    sending, release = Event(), Event()

    def worker():
        close_old_connections()
        set_rls_context(row.org_id)
        try:
            start.wait(timeout=10)
            _deliver_confirmation(row.pk, row.org_id)
        finally:
            clear_rls_context()
            close_old_connections()

    def transport(**_):
        assert not connection.in_atomic_block
        sending.set()
        assert release.wait(timeout=15)

    with patch("webforms.tasks.send_email", side_effect=transport) as sender:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker) for _ in range(2)]
            try:
                assert sending.wait(timeout=10)
                done, pending = wait(futures, timeout=10, return_when=FIRST_COMPLETED)
                assert len(done) == len(pending) == 1
                for future in done:
                    future.result()
            finally:
                release.set()
            for future in futures:
                future.result(timeout=10)
        assert sender.call_count == 1
    set_rls_context(row.org_id)
    row.refresh_from_db()
    assert row.confirmation_completed_at and not row.confirmation_claim_id


@pytest.mark.parametrize(
    "language,expected", [("es", "es"), ("en", "en"), ("fr", "en")]
)
def test_iframe_language_is_allowlisted(
    form, unauthenticated_client, language, expected
):
    response = unauthenticated_client.get(
        f"/api/public/forms/{form.org_id}/{form.pk}/embed/?lang={language}"
    )
    assert response.status_code == 200
    assert f'<html lang="{expected}">' in response.content.decode()
    assert "payload.submission_language" in response.content.decode()


@pytest.mark.parametrize("script", ["embed.js", "connect.js"])
def test_embedded_scripts_send_host_language(form, unauthenticated_client, script):
    response = unauthenticated_client.get(
        f"/api/public/forms/{form.org_id}/{form.pk}/{script}"
    )
    assert response.status_code == 200
    body = response.content.decode()
    assert "form.closest('[lang]') || document.documentElement" in body
    assert "payload.submission_language" in body


def test_legacy_nested_values_remain_readable_after_form_edit(form):
    row = submit(form)
    row.payload["custom_fields"] = {
        "legacy_details": {"Budget": 1000, "Approved": True}
    }
    form.fields.filter(lead_field="description").delete()
    rows = submission_rows(row)
    assert {"label": "Message", "value": "Private message"} in rows
    assert {"label": "Legacy details", "value": "Budget: 1000\nApproved: Yes"} in rows
