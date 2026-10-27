import uuid
from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
import requests
from cryptography.fernet import Fernet
from django.utils import timezone

from common.google_integration import (
    GoogleAPI,
    GoogleError,
    clear_unusable_connection,
    encrypt,
)
from common.google_sync import sync_gmail
from common.models import (
    GoogleCalendarEvent,
    GoogleCalendarMirror,
    GoogleConnection,
    GoogleMailActivity,
    SalesAppointment,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def connection(admin_profile, settings):
    settings.GOOGLE_INTEGRATION_ENCRYPTION_KEY = Fernet.generate_key().decode()
    settings.GOOGLE_INTEGRATION_CLIENT_ID = "test-client"
    settings.GOOGLE_INTEGRATION_CLIENT_SECRET = "test-secret"
    return GoogleConnection.objects.create(
        org=admin_profile.org,
        profile=admin_profile,
        service="gmail",
        email="owner@example.com",
        subject="google-user",
        status="connected",
        encrypted_refresh_token=encrypt("private-test-token"),
    )


def cached_message(connection):
    return GoogleMailActivity.objects.create(
        org=connection.org,
        connection=connection,
        message_id="m1",
        thread_id="t1",
        contact_email="client@example.com",
        sender="client@example.com",
        occurred_at=timezone.now(),
        direction="received",
        encrypted_body=encrypt("Private"),
    )


def test_connect_requires_explicit_disclosure_acceptance(admin_client, connection):
    with patch("common.views.google_integration_views.begin") as begin:
        for payload in (
            {},
            {"disclosure_accepted": "true"},
            {"disclosure_accepted": False},
        ):
            assert (
                admin_client.post(
                    "/api/integrations/google/connect/gmail/", payload, format="json"
                ).status_code
                == 400
            )
        begin.assert_not_called()
        begin.return_value = {"url": "https://accounts.google.com/", "state": "test"}
        assert (
            admin_client.post(
                "/api/integrations/google/connect/gmail/",
                {"disclosure_accepted": True},
                format="json",
            ).status_code
            == 200
        )
        begin.assert_called_once()


def test_empty_contacts_do_not_enumerate_mailbox(connection):
    cached_message(connection)
    api = Mock()
    sync_gmail(connection, api)
    api.get.assert_not_called()
    assert not connection.mail_activity.exists()


def test_disconnect_single_service_does_not_revoke_other_grants(
    admin_client, connection
):
    calendar = GoogleConnection.objects.create(
        org=connection.org,
        profile=connection.profile,
        service="calendar",
        subject=connection.subject,
    )
    with patch("common.google_integration.requests.post") as post:
        assert (
            admin_client.post(
                "/api/integrations/google/",
                {"service": "gmail", "operation": "disconnect"},
                format="json",
            ).status_code
            == 200
        )
    post.assert_not_called()
    assert GoogleConnection.objects.filter(pk=calendar.pk).exists()


def revoke(client, **extra):
    return client.post(
        "/api/integrations/google/",
        {"service": "gmail", "operation": "revoke", **extra},
        format="json",
    )


def test_revoke_requires_confirmation_and_own_connection(
    admin_client, user_client, connection
):
    with patch("common.google_integration.requests.post") as post:
        assert revoke(admin_client).status_code == 400
        assert revoke(user_client, confirm_revoke=True).status_code == 404
        post.assert_not_called()


@pytest.mark.parametrize("status,error", [(200, None), (400, "invalid_token")])
def test_revoke_cleans_matching_profile_only(
    admin_client, connection, user_profile, status, error
):
    cached_message(connection)
    calendar = GoogleConnection.objects.create(
        org=connection.org,
        profile=connection.profile,
        service="calendar",
        subject=connection.subject,
    )
    other = GoogleConnection.objects.create(
        org=user_profile.org,
        profile=user_profile,
        service="gmail",
        subject=connection.subject,
    )
    response = Mock(status_code=status)
    response.json.return_value = {"error": error}
    with patch(
        "common.google_integration.requests.post", return_value=response
    ) as post:
        assert revoke(admin_client, confirm_revoke=True).status_code == 200
    assert post.call_args.args == ("https://oauth2.googleapis.com/revoke",)
    assert post.call_args.kwargs["data"] == {"token": "private-test-token"}
    assert not GoogleConnection.objects.filter(
        pk__in=[connection.pk, calendar.pk]
    ).exists()
    assert not GoogleMailActivity.objects.exists()
    assert GoogleConnection.objects.filter(pk=other.pk).exists()


def test_revoke_preserves_different_google_account(admin_client, connection):
    other = GoogleConnection.objects.create(
        org=connection.org,
        profile=connection.profile,
        service="calendar",
        subject="different-user",
        email="other@example.com",
    )
    with patch(
        "common.google_integration.requests.post", return_value=Mock(status_code=200)
    ):
        assert revoke(admin_client, confirm_revoke=True).status_code == 200
    assert GoogleConnection.objects.filter(pk=other.pk).exists()


@pytest.mark.parametrize(
    "failure", [Mock(status_code=503), requests.Timeout("secret response")]
)
def test_revoke_failure_preserves_retry_and_hides_provider_details(
    admin_client, connection, failure
):
    kwargs = (
        {"side_effect": failure}
        if isinstance(failure, Exception)
        else {"return_value": failure}
    )
    with patch("common.google_integration.requests.post", **kwargs):
        result = revoke(admin_client, confirm_revoke=True)
    assert result.status_code == 400
    assert "secret" not in str(result.data)
    connection.refresh_from_db()
    assert connection.encrypted_refresh_token


@pytest.mark.parametrize(
    "error,cleared", [("invalid_grant", True), ("invalid_client", False)]
)
def test_refresh_rejection_only_cleans_revoked_or_expired_grants(
    connection, error, cleared
):
    cached_message(connection)
    generation = connection.generation
    response = Mock(status_code=400)
    response.json.return_value = {"error": error}
    with (
        patch("common.google_integration.requests.post", return_value=response),
        pytest.raises(GoogleError),
    ):
        GoogleAPI(connection)
    connection.refresh_from_db()
    assert connection.mail_activity.exists() is not cleared
    assert bool(connection.encrypted_refresh_token) is not cleared
    if cleared:
        assert connection.status == "reconnect" and connection.generation != generation


def test_revocation_does_not_erase_newly_connected_generation(connection):

    cached_message(connection)
    GoogleConnection.objects.filter(pk=connection.pk).update(generation=uuid.uuid4())
    clear_unusable_connection(connection)
    assert connection.mail_activity.exists()


def test_revoke_tries_calendar_if_gmail_token_is_already_invalid(
    admin_client, connection
):
    GoogleConnection.objects.create(
        org=connection.org,
        profile=connection.profile,
        service="calendar",
        subject=connection.subject,
        encrypted_refresh_token=encrypt("calendar-token"),
    )
    invalid = Mock(status_code=400)
    invalid.json.return_value = {"error": "invalid_token"}

    def response(url, *, data, timeout):
        return (
            invalid if data["token"] == "private-test-token" else Mock(status_code=200)
        )

    with patch("common.google_integration.requests.post", side_effect=response) as post:
        assert revoke(admin_client, confirm_revoke=True).status_code == 200
    assert any(
        call.kwargs["data"]["token"] == "calendar-token" for call in post.call_args_list
    )
    assert not GoogleConnection.objects.filter(profile=connection.profile).exists()


def test_refresh_timeout_keeps_cached_mail_for_retry(connection):
    cached_message(connection)
    with (
        patch("common.google_integration.requests.post", side_effect=requests.Timeout),
        pytest.raises(GoogleError),
    ):
        GoogleAPI(connection)
    connection.refresh_from_db()
    assert connection.mail_activity.exists()
    assert connection.encrypted_refresh_token
    assert connection.status == "connected"


def test_revoke_preserves_connection_replaced_during_provider_request(
    admin_client, connection
):

    generation = uuid.uuid4()

    def response(*args, **kwargs):
        GoogleConnection.objects.filter(pk=connection.pk).update(generation=generation)
        return Mock(status_code=200)

    with patch("common.google_integration.requests.post", side_effect=response):
        assert revoke(admin_client, confirm_revoke=True).status_code == 200
    connection.refresh_from_db()
    assert connection.generation == generation


def test_expired_calendar_grant_clears_google_cache_but_preserves_crm_appointment(
    connection,
):

    connection.service = "calendar"
    connection.save(update_fields=["service"])
    appointment = SalesAppointment.objects.create(
        org=connection.org,
        host=connection.profile,
        created_by=connection.profile.user,
        title="Keep CRM meeting",
        starts_at=timezone.now(),
        ends_at=timezone.now() + timedelta(hours=1),
    )
    GoogleCalendarEvent.objects.create(
        org=connection.org,
        connection=connection,
        external_id="event",
        title="Private event",
        starts_at=appointment.starts_at,
        ends_at=appointment.ends_at,
    )
    GoogleCalendarMirror.objects.create(
        org=connection.org,
        connection=connection,
        appointment=appointment,
        external_id="event",
    )
    response = Mock(status_code=400)
    response.json.return_value = {"error": "invalid_grant"}
    with (
        patch("common.google_integration.requests.post", return_value=response),
        pytest.raises(GoogleError),
    ):
        GoogleAPI(connection)
    assert not connection.events.exists()
    assert not connection.mirrors.exists()
    assert SalesAppointment.objects.filter(pk=appointment.pk).exists()
