"""Website submissions: tenant isolation, identity, retries and delivery."""

import uuid
from unittest.mock import patch

import pytest
from django.core import mail
from django.core.cache import cache

from common.models import Comment, Notification
from contacts.models import Contact
from webforms.models import WebForm, WebFormField, WebFormSubmission
from webforms.service import submit_form
from webforms.tasks import retry_pending_webform_emails, send_webform_submission_email

pytestmark = pytest.mark.django_db


@pytest.fixture
def form(org_a, admin_profile):
    form = WebForm.objects.create(
        org=org_a,
        name="Website enquiry",
        target_model="Contact",
        assign_to=admin_profile,
        is_published=True,
        allowed_origins=["https://example.com"],
    )
    for key in ("first_name", "email", "description", "city", "phone"):
        WebFormField.objects.create(
            org=org_a,
            form=form,
            source="lead",
            lead_field=key,
            label=key,
            is_required=key in ("first_name", "email"),
        )
    cache.clear()
    return form


def post(client, form, **payload):
    return client.post(
        f"/api/public/forms/{form.org_id}/{form.pk}/submit/",
        {"first_name": "Pat", "email": "pat@example.com", **payload},
        format="json",
        HTTP_ORIGIN="https://example.com",
    )


def test_creates_contact_and_notification_not_a_lead(
    form, unauthenticated_client, admin_profile
):
    assert (
        post(unauthenticated_client, form, description="Please call").status_code == 200
    )
    row = WebFormSubmission.objects.get()
    assert row.contact.first_name == "Pat"
    assert row.lead is None
    assert row.contact.assigned_to.get() == admin_profile
    notification = Notification.objects.get(verb="webform.submitted")
    assert notification.link == f"/contacts/{row.contact_id}"
    assert notification.org_id == form.org_id
    assert Comment.objects.filter(
        object_id=row.contact_id, comment__contains="Please call"
    ).exists()


def test_existing_contact_is_not_overwritten(form, admin_profile):
    original = Contact.objects.create(
        org=form.org,
        first_name="Original",
        email="PAT@example.com",
        city="Miami",
        stage="QUALIFIED",
    )
    row = submit_form(
        form,
        {
            "first_name": "Attacker",
            "email": "pat@example.com",
            "city": "Boston",
            "description": "Second enquiry",
        },
    )
    original.refresh_from_db()
    assert row.contact_id == original.pk
    assert row.status == "accepted_duplicate"
    assert (
        original.first_name == "Original"
        and original.city == "Miami"
        and original.stage == "QUALIFIED"
    )
    assert not original.assigned_to.exists()
    assert Contact.objects.count() == 1


def test_same_email_in_other_tenant_is_separate(form, org_b):
    from common.testing import rls_org

    with rls_org(org_b):
        other = Contact.objects.create(
            org=org_b, first_name="Other", email="pat@example.com"
        )
    row = submit_form(form, {"first_name": "Pat", "email": "pat@example.com"})
    assert row.contact_id != other.pk
    assert row.contact.org_id == form.org_id


def test_retry_does_not_create_second_submission_comment_or_alert(
    form, unauthenticated_client
):
    request_id = str(uuid.uuid4())
    for _ in range(2):
        assert (
            post(
                unauthenticated_client, form, request_id=request_id, description="Hello"
            ).status_code
            == 200
        )
    assert (
        WebFormSubmission.objects.count()
        == Contact.objects.count()
        == Notification.objects.filter(verb="webform.submitted").count()
        == 1
    )
    assert Comment.objects.count() == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("first_name", ""),
        ("email", ""),
        ("email", "invalid"),
        ("phone", "12"),
        ("city", "123"),
    ],
)
def test_validates_identity_and_contact_properties(
    form, unauthenticated_client, field, value
):
    assert post(unauthenticated_client, form, **{field: value}).status_code == 400
    assert not Contact.objects.exists()
    assert not Notification.objects.exists()


def test_ignores_ownership_pipeline_and_unmapped_properties(
    form, unauthenticated_client, profile_b
):
    assert (
        post(
            unauthenticated_client,
            form,
            org=str(profile_b.org_id),
            assigned_to=[str(profile_b.pk)],
            stage="QUALIFIED",
            appointment_at="2026-12-01",
            organization="Injected",
            is_sample=True,
        ).status_code
        == 200
    )
    contact = Contact.objects.get()
    assert contact.org_id == form.org_id and contact.stage == "LEAD"
    assert (
        not contact.organization
        and not contact.is_sample
        and not contact.appointment_at
    )


def test_origin_must_be_exact_even_with_referer_fallback(form, unauthenticated_client):
    url = f"/api/public/forms/{form.org_id}/{form.pk}/submit/"
    assert (
        unauthenticated_client.post(
            url, {}, format="json", HTTP_REFERER="https://example.com.evil.test/path"
        ).status_code
        == 403
    )


def test_disabled_organization_and_unpublished_form_reject(
    form, unauthenticated_client
):
    form.is_published = False
    form.save()
    assert post(unauthenticated_client, form).status_code == 404
    form.is_published = True
    form.save()
    form.org.is_active = False
    form.org.save()
    assert post(unauthenticated_client, form).status_code == 404


def test_honeypot_does_not_create_contact_or_alert(form, unauthenticated_client):
    assert (
        post(unauthenticated_client, form, company_website_url="spam").status_code
        == 200
    )
    assert not Contact.objects.exists() and not Notification.objects.exists()


def test_queue_failure_keeps_success_and_recoverable_mail(
    form, unauthenticated_client, django_capture_on_commit_callbacks
):
    with (
        patch(
            "webforms.tasks.send_webform_submission_email.delay",
            side_effect=ConnectionError,
        ),
        django_capture_on_commit_callbacks(execute=True),
    ):
        assert post(unauthenticated_client, form).status_code == 200
    row = WebFormSubmission.objects.get()
    assert row.email_completed_at is None
    with patch("webforms.tasks.send_webform_submission_email.delay") as queue:
        retry_pending_webform_emails()
    queue.assert_any_call(str(row.pk), str(form.org_id))


def test_email_delivery_is_individual_and_retry_safe(form, user_profile):
    form.notify_profiles.add(user_profile, form.assign_to)
    row = submit_form(form, {"first_name": "Pat", "email": "pat@example.com"})
    mail.outbox.clear()
    send_webform_submission_email(str(row.pk), str(form.org_id))
    send_webform_submission_email(str(row.pk), str(form.org_id))
    assert len(mail.outbox) == 2
    assert all(len(message.to) == 1 for message in mail.outbox)
    assert f"/contacts/{row.contact_id}" in mail.outbox[0].alternatives[0][0]


def test_foreign_and_inactive_recipients_are_skipped(form, profile_b, user_profile):
    form.notify_profiles.add(profile_b, user_profile)
    user_profile.is_active = False
    user_profile.save()
    row = submit_form(form, {"first_name": "Pat", "email": "pat@example.com"})
    assert Notification.objects.filter(verb="webform.submitted").count() == 1
    mail.outbox.clear()
    send_webform_submission_email(str(row.pk), str(form.org_id))
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [form.assign_to.user.email]


def test_notifications_can_be_switched_off(form):
    form.notify_in_app = form.notify_email = False
    form.save()
    row = submit_form(form, {"first_name": "Pat", "email": "pat@example.com"})
    mail.outbox.clear()
    send_webform_submission_email(str(row.pk), str(form.org_id))
    assert not Notification.objects.exists() and not mail.outbox


def test_submission_payloads_are_admin_only(form, user_client):
    assert user_client.get(f"/api/webforms/{form.pk}/submissions/").status_code == 403


def test_contact_form_creation_seeds_identifying_fields(admin_client):
    response = admin_client.post(
        "/api/webforms/", {"name": "Website", "target_model": "Contact"}, format="json"
    )
    assert response.status_code == 201, response.data
    assert [r["lead_field"] for r in response.data["fields"]] == [
        "first_name",
        "email",
        "description",
    ]
    assert all(r["is_required"] for r in response.data["fields"][:2])
    assert "connect.js" in response.data["connector_js"]


@pytest.mark.parametrize(
    "key", ["appointment_at", "stage", "assigned_to", "website", "company_name"]
)
def test_disallows_non_contact_or_protected_mapping(admin_client, form, key):
    response = admin_client.put(
        f"/api/webforms/{form.pk}/",
        {"fields": [{"source": "lead", "lead_field": key, "label": key}]},
        format="json",
    )
    assert response.status_code == 400


def test_cannot_remove_name_from_published_contact_form(form, admin_client):
    response = admin_client.put(
        f"/api/webforms/{form.pk}/",
        {"fields": [{"source": "lead", "lead_field": "email", "label": "Email"}]},
        format="json",
    )
    assert response.status_code == 400


def test_connector_serves_only_mapping_and_public_config(form, unauthenticated_client):
    field = form.fields.get(lead_field="email")
    field.external_name = "your-email"
    field.save()
    form.captcha_secret = "must-not-be-exposed"
    form.save()
    response = unauthenticated_client.get(
        f"/api/public/forms/{form.org_id}/{form.pk}/connect.js"
    )
    text = response.content.decode()
    assert response.status_code == 200
    assert '"externalName": "your-email"' in text
    assert "must-not-be-exposed" not in text and form.assign_to.user.email not in text
    assert response["Cache-Control"] == "no-store"


def test_notification_respects_record_permissions(form, user_profile):
    from common.models import CRMRole
    from common.rbac import default_rules

    rules = default_rules()
    rules["contacts"]["view"] = "none"
    user_profile.access_role = CRMRole.objects.create(
        org=form.org, name="No contacts", rules=rules
    )
    user_profile.save()
    form.notify_profiles.add(user_profile)
    row = submit_form(form, {"first_name": "Pat", "email": "pat@example.com"})
    assert not Notification.objects.filter(recipient=user_profile).exists()
    mail.outbox.clear()
    send_webform_submission_email(str(row.pk), str(form.org_id))
    assert len(mail.outbox) == 1 and mail.outbox[0].to == [form.assign_to.user.email]


def test_partial_email_failure_does_not_resend_completed_recipient(form, user_profile):
    form.notify_profiles.add(user_profile)
    row = submit_form(form, {"first_name": "Pat", "email": "pat@example.com"})
    with patch(
        "webforms.tasks.send_email", side_effect=[None, ConnectionError]
    ) as sender:
        with pytest.raises(ConnectionError):
            send_webform_submission_email(str(row.pk), str(form.org_id))
        first = sender.call_args_list[0].kwargs["recipients"]
    from common.tasks import set_rls_context

    set_rls_context(form.org_id)
    row.refresh_from_db()
    assert len(row.email_delivered_to) == 1 and row.email_completed_at is None
    with patch("webforms.tasks.send_email") as sender:
        send_webform_submission_email(str(row.pk), str(form.org_id))
    assert sender.call_count == 1 and sender.call_args.kwargs["recipients"] != first


def test_api_errors_do_not_disclose_duplicate_identity(form, unauthenticated_client):
    first = post(unauthenticated_client, form)
    second = post(unauthenticated_client, form)
    assert first.data == second.data and first.status_code == second.status_code == 200
    assert Contact.objects.count() == 1 and WebFormSubmission.objects.count() == 2


def test_duplicate_input_mapping_returns_validation_error(form, admin_client):
    rows = [
        {"source": "lead", "lead_field": key, "external_name": "same", "label": key}
        for key in ("first_name", "email")
    ]
    response = admin_client.put(
        f"/api/webforms/{form.pk}/", {"fields": rows}, format="json"
    )
    assert response.status_code == 400


def test_custom_contact_property_maps_to_contact_json(
    form, admin_client, unauthenticated_client
):
    from common.models import CustomFieldDefinition

    field = CustomFieldDefinition.objects.create(
        org=form.org,
        target_model="Contact",
        key="interest",
        label="Interest",
        field_type="text",
    )
    rows = [
        {"source": "lead", "lead_field": key, "label": key}
        for key in ("first_name", "email")
    ]
    rows.append(
        {
            "source": "custom",
            "custom_field": str(field.pk),
            "label": "Interest",
            "external_name": "your-interest",
        }
    )
    response = admin_client.put(
        f"/api/webforms/{form.pk}/", {"fields": rows}, format="json"
    )
    assert response.status_code == 200, response.data
    assert post(unauthenticated_client, form, interest="CRM setup").status_code == 200
    assert Contact.objects.get().custom_fields == {"interest": "CRM setup"}


@pytest.mark.django_db(transaction=True)
def test_concurrent_forms_create_one_contact(org_a):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections, connection

    from common.tasks import clear_rls_context, set_rls_context
    from common.testing import restore_rls_context

    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL concurrency and unique constraints")
    forms = [
        WebForm.objects.create(
            org=org_a, target_model="Contact", name=f"Concurrent {i}"
        )
        for i in range(2)
    ]
    barrier = Barrier(2)

    def submit(pk):
        close_old_connections()
        set_rls_context(org_a.pk)
        try:
            form = WebForm.objects.get(pk=pk, org=org_a)
            barrier.wait(timeout=10)
            return submit_form(
                form, {"first_name": "Pat", "email": "same@example.com"}
            ).contact_id
        finally:
            clear_rls_context()
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(submit, [form.pk for form in forms]))
    restore_rls_context()
    assert ids[0] == ids[1]
    assert Contact.objects.filter(org=org_a).count() == 1
    assert WebFormSubmission.objects.filter(org=org_a).count() == 2
