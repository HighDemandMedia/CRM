# ruff: noqa: F811 -- Imported pytest fixtures are injected by name.
import base64
import uuid
from email import policy
from email.parser import BytesParser
from unittest.mock import patch

import pytest
from django.core.cache import cache

from accounts.models import Account
from common.google_integration import GMAIL_SEND_SCOPE, GoogleError, decrypt
from common.models import Comment, GoogleMailActivity, GoogleMailSendOperation
from common.record_history import history_for
from common.tests.test_google_integrations import google_settings  # noqa: F401
from common.tests.test_record_mail import conn, endpoint, message  # noqa: F401
from contacts.models import Contact

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def fresh_throttle():
    cache.clear()


@pytest.fixture
def setup_mail(conn, org_a):
    conn.scopes = [GMAIL_SEND_SCOPE]
    conn.save(update_fields=["scopes"])
    contact = Contact.objects.create(org=org_a, email="client@example.com")
    original = message(conn, contact)
    return contact, original


def payload(**overrides):
    return dict(
        action="send",
        request_id=str(uuid.uuid4()),
        to=["client@example.com"],
        subject="Proposal",
        body="Hello client",
        **overrides,
    )


def post(client, record, data, kind="contact"):
    return client.post(endpoint(record, kind) + "actions/", data, format="json")


def test_send_is_personal_cached_and_idempotent(admin_client, conn, setup_mail):
    contact, _ = setup_mail
    data = payload()
    with patch("common.google_mail_actions.GoogleAPI") as provider:
        provider.return_value.request.return_value = {
            "id": "new-message",
            "threadId": "new-thread",
        }
        result = post(admin_client, contact, data)
        assert result.status_code == 200, result.data
        duplicate = post(admin_client, contact, data)
        assert duplicate.data == result.data
        assert provider.call_count == 1
        assert provider.call_args.args[0].pk == conn.pk
        raw = provider.return_value.request.call_args.kwargs["body"]["raw"]
        mime = BytesParser(policy=policy.default).parsebytes(
            base64.urlsafe_b64decode(raw)
        )
        assert mime["From"] == conn.email
        assert mime["To"] == contact.email
        assert mime.get_body().get_content().strip() == data["body"]
    cached = GoogleMailActivity.objects.get(message_id="new-message")
    assert cached.connection == conn and decrypt(cached.encrypted_body) == data["body"]
    assert post(admin_client, contact, {**data, "body": "different"}).status_code == 409


def test_uncertain_send_cannot_be_retried(admin_client, setup_mail):
    contact, _ = setup_mail
    data = payload()
    with patch("common.google_mail_actions.GoogleAPI") as provider:
        provider.return_value.request.side_effect = GoogleError()
        assert post(admin_client, contact, data).status_code == 409
        assert post(admin_client, contact, data).status_code == 409
        assert provider.return_value.request.call_count == 1
    assert GoogleMailSendOperation.objects.get().status == "unknown"


def test_reply_preserves_thread_headers_and_forward_starts_new(
    admin_client, setup_mail
):
    contact, original = setup_mail
    with patch("common.google_mail_actions.GoogleAPI") as provider:
        api = provider.return_value
        api.get.return_value = {
            "payload": {
                "headers": [{"name": "Message-ID", "value": "<original@example.com>"}]
            }
        }
        api.request.return_value = {"id": "reply", "threadId": original.thread_id}
        data = {**payload(), "action": "reply", "message": str(original.pk)}
        assert post(admin_client, contact, data).status_code == 200
        body = api.request.call_args.kwargs["body"]
        mime = BytesParser(policy=policy.default).parsebytes(
            base64.urlsafe_b64decode(body["raw"])
        )
        assert body["threadId"] == original.thread_id
        assert mime["In-Reply-To"] == "<original@example.com>"
        assert mime["Subject"] == original.subject
        api.request.return_value = {"id": "forward", "threadId": "forward-thread"}
        assert (
            post(
                admin_client,
                contact,
                {**payload(), "action": "forward", "message": str(original.pk)},
            ).status_code
            == 200
        )
        assert "threadId" not in api.request.call_args.kwargs["body"]


def test_scope_validation_and_cross_tenant_source_guards(
    admin_client, org_b_client, setup_mail, conn
):
    contact, original = setup_mail
    with patch("common.google_mail_actions.GoogleAPI") as provider:
        assert post(org_b_client, contact, payload()).status_code in (403, 404)
        assert (
            post(
                admin_client,
                contact,
                {**payload(), "subject": "Bad\r\nBcc: stolen@example.com"},
            ).status_code
            == 400
        )
        assert (
            post(
                admin_client,
                contact,
                {**payload(), "action": "reply", "message": str(uuid.uuid4())},
            ).status_code
            == 404
        )
        conn.scopes = []
        conn.save(update_fields=["scopes"])
        assert post(admin_client, contact, payload()).status_code == 409
        provider.assert_not_called()


def test_comment_becomes_shared_record_note_without_private_body(
    admin_client, setup_mail, conn
):
    contact, original = setup_mail
    result = post(
        admin_client,
        contact,
        {"action": "comment", "message": str(original.pk), "body": "Please follow up"},
    )
    assert result.status_code == 200, result.data
    note = Comment.objects.get(pk=result.data["id"])
    assert note.object_id == contact.pk and note.org == conn.org
    assert note.is_internal and note.commented_by == conn.profile
    assert original.subject in note.comment and "Please follow up" in note.comment
    assert "Private message" not in note.comment
    assert any(row["description"] == "Note added" for row in history_for(contact))
    assert not GoogleMailSendOperation.objects.exists()


def test_company_comment_scoped_and_search_matches_encrypted_body(
    admin_client, setup_mail, org_a
):
    contact, original = setup_mail
    company = Account.objects.create(org=org_a, name="Client business")
    company.contacts.add(contact)
    result = post(
        admin_client,
        company,
        {"action": "comment", "message": str(original.pk), "body": "Team comment"},
        "company",
    )
    assert result.status_code == 200, result.data
    assert Comment.objects.get().content_type.model == "account"
    response = admin_client.get(endpoint(company, "company"), {"q": "private MESSAGE"})
    assert len(response.data["results"]) == 1
    assert "body" not in response.data["results"][0]


def test_company_history_real_changes_only(org_a):
    company = Account.objects.create(org=org_a, name="Before")
    company.name = "After"
    company.save()
    company.save()
    history = history_for(company)
    assert len(history) == 2
    assert history[0]["changes"]["name"]["before"] == "Before"
    assert history[0]["changes"]["name"]["after"] == "After"
    assert history[1]["action"] == "CREATE"


def test_shared_comment_readable_by_team_but_mail_stays_private(
    admin_client, user_client, user_profile, setup_mail
):
    contact, original = setup_mail
    contact.assigned_to.add(user_profile)
    result = post(
        admin_client,
        contact,
        {"action": "comment", "message": str(original.pk), "body": "Team follow-up"},
    )
    assert result.status_code == 200
    detail = user_client.get(f"/api/contacts/{contact.pk}/")
    assert detail.status_code == 200, detail.data
    assert any("Team follow-up" in note["comment"] for note in detail.data["comments"])
    assert detail.data["email_activity"] == []
    assert (
        post(
            user_client,
            contact,
            {
                "action": "comment",
                "message": str(original.pk),
                "body": "Private source",
            },
        ).status_code
        == 404
    )


def test_record_action_permissions_enforced(
    user_client, user_profile, org_a, google_settings
):
    from common.google_integration import encrypt
    from common.models import GoogleConnection
    from common.tests.test_crm_roles import assign

    contact = Contact.objects.create(
        org=org_a, email="client@example.com", created_by=user_profile.user
    )
    mailbox = GoogleConnection.objects.create(
        org=org_a,
        profile=user_profile,
        service="gmail",
        email=user_profile.user.email,
        status="connected",
        scopes=[GMAIL_SEND_SCOPE],
        encrypted_refresh_token=encrypt("test-token"),
    )
    original = message(mailbox, contact)
    contact.assigned_to.add(user_profile)
    assign(user_profile, edit="none", notes="none")
    with patch("common.google_mail_actions.GoogleAPI") as provider:
        assert post(user_client, contact, payload()).status_code == 403
        assert (
            post(
                user_client,
                contact,
                {"action": "comment", "message": str(original.pk), "body": "Denied"},
            ).status_code
            == 403
        )
        provider.assert_not_called()


def test_unchanged_owner_payload_does_not_add_activity(
    admin_client, admin_profile, org_a
):
    from common.models import Activity

    contact = Contact.objects.create(org=org_a, first_name="Client")
    contact.assigned_to.add(admin_profile)
    previous = Activity.objects.filter(entity_id=contact.pk).count()
    response = admin_client.patch(
        f"/api/contacts/{contact.pk}/",
        {"assigned_to": [str(admin_profile.pk)]},
        format="json",
    )
    assert response.status_code == 200, response.data
    assert Activity.objects.filter(entity_id=contact.pk).count() == previous
