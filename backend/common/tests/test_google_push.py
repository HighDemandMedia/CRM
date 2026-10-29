import base64
import json
from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from cryptography.fernet import Fernet
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Account
from common.google_integration import GoogleError
from common.google_push import renew_watch, request_mail_sync
from common.models import GoogleConnection, GoogleMailActivity
from common.tasks import process_gmail_notification, sync_google_connection
from contacts.models import Contact

pytestmark = pytest.mark.django_db
PATH = "/api/integrations/google/gmail/push/"


@pytest.fixture(autouse=True)
def push_settings(settings):
    settings.GOOGLE_GMAIL_PROJECT_ID = "gmail-test"
    settings.GOOGLE_GMAIL_PUSH_TOPIC = "projects/gmail-test/topics/mail"
    settings.GOOGLE_GMAIL_PUSH_SUBSCRIPTION = "projects/gmail-test/subscriptions/mail"
    settings.GOOGLE_GMAIL_PUSH_AUDIENCE = "https://api.example.com" + PATH
    settings.GOOGLE_GMAIL_PUSH_SERVICE_ACCOUNT = (
        "push@gmail-test.iam.gserviceaccount.com"
    )
    settings.GOOGLE_INTEGRATION_ENCRYPTION_KEY = Fernet.generate_key().decode()


@pytest.fixture
def conn(admin_profile, org_a):
    return GoogleConnection.objects.create(
        org=org_a,
        profile=admin_profile,
        service="gmail",
        status="connected",
        email="owner@example.com",
        oauth_project_id="gmail-test",
        history_id="100",
    )


def envelope(**overrides):
    return {
        "subscription": "projects/gmail-test/subscriptions/mail",
        "message": {
            "data": base64.b64encode(
                json.dumps(
                    {
                        "emailAddress": "owner@example.com",
                        "historyId": "101",
                        **overrides,
                    }
                ).encode()
            ).decode()
        },
    }


def verified():
    return {"email": "push@gmail-test.iam.gserviceaccount.com", "email_verified": True}


def test_push_requires_google_identity_and_exact_subscription():
    client = APIClient()
    with patch("common.tasks.process_gmail_notification.delay") as queue:
        assert client.post(PATH, envelope(), format="json").status_code == 401
        with patch(
            "common.views.google_push_views.verify_oauth2_token",
            return_value={"email": "attacker@example.com", "email_verified": True},
        ):
            assert (
                client.post(
                    PATH, envelope(), format="json", HTTP_AUTHORIZATION="Bearer fake"
                ).status_code
                == 403
            )
        with patch(
            "common.views.google_push_views.verify_oauth2_token",
            return_value=verified(),
        ):
            data = envelope()
            data["subscription"] = "projects/other/subscriptions/mail"
            assert (
                client.post(
                    PATH, data, format="json", HTTP_AUTHORIZATION="Bearer fake"
                ).status_code
                == 400
            )
            assert (
                client.post(
                    PATH,
                    envelope(historyId="invalid"),
                    format="json",
                    HTTP_AUTHORIZATION="Bearer fake",
                ).status_code
                == 400
            )
        queue.assert_not_called()


def test_push_acknowledges_only_after_queueing(settings):
    with (
        patch(
            "common.views.google_push_views.verify_oauth2_token",
            return_value=verified(),
        ) as verify,
        patch("common.tasks.process_gmail_notification.delay") as queue,
    ):
        response = APIClient().post(
            PATH, envelope(), format="json", HTTP_AUTHORIZATION="Bearer token"
        )
        assert response.status_code == 204
        assert verify.call_args.args[2] == settings.GOOGLE_GMAIL_PUSH_AUDIENCE
        queue.assert_called_once_with("owner@example.com", "101", "gmail-test")
        queue.side_effect = RuntimeError("broker unavailable")
        assert (
            APIClient()
            .post(PATH, envelope(), format="json", HTTP_AUTHORIZATION="Bearer token")
            .status_code
            == 503
        )


def test_disabled_push_cannot_enqueue(settings):
    settings.GOOGLE_GMAIL_PUSH_TOPIC = ""
    assert APIClient().post(PATH, envelope(), format="json").status_code == 503


def test_invalid_google_token_cannot_enqueue():
    with (
        patch(
            "common.views.google_push_views.verify_oauth2_token", side_effect=ValueError
        ),
        patch("common.tasks.process_gmail_notification.delay") as queue,
    ):
        assert (
            APIClient()
            .post(PATH, envelope(), format="json", HTTP_AUTHORIZATION="Bearer invalid")
            .status_code
            == 401
        )
        queue.assert_not_called()


def test_failed_queue_can_retry(conn, django_capture_on_commit_callbacks):
    with (
        patch("common.tasks.sync_google_connection.delay", side_effect=RuntimeError),
        pytest.raises(RuntimeError),
        django_capture_on_commit_callbacks(execute=True),
    ):
        request_mail_sync(conn, "101")
    conn.refresh_from_db()
    assert conn.mail_sync_requested_at is None
    with (
        patch("common.tasks.sync_google_connection.delay") as queue,
        django_capture_on_commit_callbacks(execute=True),
    ):
        request_mail_sync(conn, "101")
    queue.assert_called_once()


def test_notification_routes_only_matching_active_mailboxes(conn, user_profile, org_a):
    other = GoogleConnection.objects.create(
        org=org_a,
        profile=user_profile,
        service="gmail",
        status="connected",
        email="other@example.com",
        oauth_project_id="gmail-test",
    )
    with patch("common.google_push.request_mail_sync") as request:
        process_gmail_notification("owner@example.com", "101", "wrong-project")
        request.assert_not_called()
        process_gmail_notification("OWNER@example.com", "101", "gmail-test")
        assert [call.args[0].pk for call in request.call_args_list] == [conn.pk]
        conn.status = "disconnected"
        conn.save()
        request.reset_mock()
        process_gmail_notification("owner@example.com", "102", "gmail-test")
        request.assert_not_called()
    assert other.status == "connected"


def test_push_coalesces_and_preserves_notification_during_sync(
    conn, django_capture_on_commit_callbacks
):
    with (
        patch("common.tasks.sync_google_connection.delay") as queue,
        django_capture_on_commit_callbacks(execute=True),
    ):
        request_mail_sync(conn, "100")
        request_mail_sync(conn, "101")
        request_mail_sync(conn, "102")
    queue.assert_called_once()
    conn.refresh_from_db()
    assert conn.mail_sync_requested_at
    conn.sync_started_at = timezone.now()
    conn.mail_sync_requested_at = None
    conn.save()
    with (
        patch("common.tasks.sync_google_connection.delay") as queue,
        django_capture_on_commit_callbacks(execute=True),
    ):
        request_mail_sync(conn, "103")
    queue.assert_not_called()
    conn.refresh_from_db()
    assert conn.mail_sync_requested_at > conn.sync_started_at


def test_watch_is_all_mail_daily_and_does_not_skip_history(conn):
    api = Mock()
    api.request.return_value = {
        "historyId": "999",
        "expiration": str(int((timezone.now() + timedelta(days=7)).timestamp() * 1000)),
    }
    renew_watch(conn, api)
    api.request.assert_called_once_with(
        "POST",
        "gmail/v1/users/me/watch",
        body={"topicName": "projects/gmail-test/topics/mail"},
    )
    conn.refresh_from_db()
    assert conn.history_id == "100"
    renew_watch(conn, api)
    assert api.request.call_count == 1
    conn.mail_watch_renewed_at -= timedelta(days=2)
    renew_watch(conn, api)
    assert api.request.call_count == 2


def test_failed_watch_keeps_fallback(conn):
    api = Mock()
    api.request.side_effect = GoogleError(status=403, reconnect=True)
    renew_watch(conn, api)
    conn.refresh_from_db()
    assert conn.status == "connected"
    assert not conn.mail_watch_expires_at


def test_sync_requeues_a_notification_arriving_during_processing(conn):
    def sync(*args):
        GoogleConnection.objects.filter(pk=conn.pk).update(
            mail_sync_requested_at=timezone.now()
        )
        return False

    with (
        patch("common.google_integration.GoogleAPI"),
        patch("common.google_push.renew_watch"),
        patch("common.google_sync.sync_gmail", side_effect=sync),
        patch.object(sync_google_connection, "apply_async") as queue,
    ):
        sync_google_connection(str(conn.org_id), str(conn.pk))
    queue.assert_called_once()
    conn.refresh_from_db()
    assert conn.last_sync and conn.mail_sync_requested_at
    assert conn.sync_started_at is None


def test_sync_drains_incremental_pages_without_waiting_five_minutes(conn):
    with (
        patch("common.google_integration.GoogleAPI"),
        patch("common.google_push.renew_watch"),
        patch("common.google_sync.sync_gmail", return_value=True),
        patch.object(sync_google_connection, "apply_async") as queue,
    ):
        sync_google_connection(str(conn.org_id), str(conn.pk))
    assert queue.call_args.kwargs["countdown"] == 5


def test_mail_revision_is_private_and_only_changes_for_related_mail(
    admin_client, user_client, user_profile, org_b_client, conn, org_a
):
    contact = Contact.objects.create(
        org=org_a, first_name="Client", email="client@example.com"
    )
    contact.assigned_to.add(user_profile)
    url = f"/api/integrations/google/records/contact/{contact.pk}/mail/?view=status"
    before = admin_client.get(url)
    assert before.status_code == 200
    assert "results" not in before.data
    row = GoogleMailActivity.objects.create(
        org=org_a,
        connection=conn,
        message_id="m1",
        thread_id="t1",
        contact_email="unrelated@example.com",
        sender="unrelated@example.com",
        direction="received",
        occurred_at=timezone.now(),
    )
    assert admin_client.get(url).data["revision"] == before.data["revision"]
    row.contact_email = "client@example.com"
    row.save()
    after = admin_client.get(url).data["revision"]
    assert after != before.data["revision"]
    member = user_client.get(url)
    assert member.status_code == 200
    assert member.data["revision"] == before.data["revision"]
    assert org_b_client.get(url).status_code == 404
    company = Account.objects.create(org=org_a, name="Company")
    company.contacts.add(contact)
    company_url = (
        f"/api/integrations/google/records/company/{company.pk}/mail/?view=status"
    )
    assert admin_client.get(company_url).data["revision"] == after
    assert org_b_client.get(company_url).status_code == 404
    row.delete()
    assert admin_client.get(url).data["revision"] == before.data["revision"]
    assert admin_client.get(company_url).data["revision"] == before.data["revision"]
