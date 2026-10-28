"""Independent projects, legacy-token routing and fail-safe migration contracts."""

from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

import pytest
import requests
from cryptography.fernet import Fernet
from django.core.management.base import CommandError
from django.utils import timezone

from common.google_integration import (
    SCOPES,
    GoogleAPI,
    GoogleError,
    begin,
    complete,
    configured,
    connection_status,
    decrypt,
    encrypt,
)
from common.google_oauth_config import (
    PREFIXES,
    independent_disconnect,
    isolation_errors,
)
from common.management.commands.check_hosted_config import validate_settings
from common.models import GoogleConnection, GoogleMailActivity

pytestmark = pytest.mark.django_db


@pytest.fixture
def separate_clients(settings):
    for key, prefix in PREFIXES.items():
        setattr(settings, f"{prefix}_CLIENT_ID", f"{key}-client")
        setattr(settings, f"{prefix}_CLIENT_SECRET", f"{key}-secret")
        setattr(settings, f"{prefix}_PROJECT_ID", f"hdm-{key}")
    settings.GOOGLE_INTEGRATION_ENCRYPTION_KEY = Fernet.generate_key().decode()
    return settings


def connection(profile, service="gmail", *, legacy=False):
    return GoogleConnection.objects.create(
        org=profile.org,
        profile=profile,
        service=service,
        email="qa@example.com",
        subject="google-subject",
        status="connected",
        oauth_client_id="" if legacy else f"{service}-client",
        oauth_project_id="" if legacy else f"hdm-{service}",
        encrypted_refresh_token=encrypt(f"{service}-refresh"),
    )


def cache(conn):
    return GoogleMailActivity.objects.create(
        org=conn.org,
        connection=conn,
        message_id="test-mail",
        thread_id="thread",
        contact_email="qa@example.com",
        sender="qa@example.com",
        direction="received",
        occurred_at=timezone.now(),
        encrypted_body=encrypt("Keep on failed revoke"),
    )


def token_response(service):
    return {
        "refresh_token": "new-refresh",
        "id_token": "identity",
        "scope": " ".join(SCOPES[service]),
    }


IDENTITY = {"email": "qa@example.com", "email_verified": True, "sub": "google-subject"}


@pytest.mark.parametrize("service", ["gmail", "calendar"])
def test_authorization_exchange_and_audience_use_selected_service(
    separate_clients, admin_profile, service
):
    started = begin(admin_profile, service)
    query = parse_qs(urlparse(started["url"]).query)
    assert query["client_id"] == [f"{service}-client"]
    assert set(SCOPES[service]).issubset(query["scope"][0].split())
    other = "calendar" if service == "gmail" else "gmail"
    assert not set(SCOPES[other]).intersection(query["scope"][0].split())
    with (
        patch(
            "common.google_integration.requests.post",
            return_value=Mock(
                status_code=200, ok=True, json=lambda: token_response(service)
            ),
        ) as post,
        patch(
            "common.google_integration.verify_oauth2_token", return_value=IDENTITY
        ) as verify,
    ):
        conn = complete(admin_profile, "code", started["state"])
    assert post.call_args.kwargs["data"]["client_id"] == f"{service}-client"
    assert post.call_args.kwargs["data"]["client_secret"] == f"{service}-secret"
    assert verify.call_args.args[2] == f"{service}-client"
    assert conn.oauth_client_id == f"{service}-client"
    assert conn.oauth_project_id == f"hdm-{service}"
    assert not conn.pending_client_id and not conn.oauth_state_hash
    assert independent_disconnect(conn)


@pytest.mark.parametrize("legacy", [True, False])
@pytest.mark.parametrize("service", ["gmail", "calendar"])
def test_refresh_stays_with_issuing_client(
    separate_clients, admin_profile, legacy, service
):
    conn = connection(admin_profile, service, legacy=legacy)
    with patch(
        "common.google_integration.requests.post",
        return_value=Mock(
            status_code=200, ok=True, json=lambda: {"access_token": "test-access"}
        ),
    ) as post:
        GoogleAPI(conn)
    expected = "legacy" if legacy else service
    assert post.call_args.kwargs["data"]["client_id"] == f"{expected}-client"
    assert post.call_args.kwargs["data"]["client_secret"] == f"{expected}-secret"


def test_migration_does_not_replace_active_grant_until_success(
    separate_clients, admin_profile
):
    conn = connection(admin_profile, legacy=True)
    message = cache(conn)
    started = begin(admin_profile, "gmail")
    conn.refresh_from_db()
    assert conn.pending_client_id == "gmail-client"
    assert conn.oauth_client_id == ""
    assert decrypt(conn.encrypted_refresh_token) == "gmail-refresh"
    assert connection_status(admin_profile)["gmail"]["migration_available"]
    assert not independent_disconnect(conn)
    with (
        patch(
            "common.google_integration.token_request",
            return_value={"id_token": "id", "scope": ""},
        ),
        patch("common.google_integration.verify_oauth2_token", return_value=IDENTITY),
        pytest.raises(GoogleError, match="permissions"),
    ):
        complete(admin_profile, "code", started["state"])
    conn.refresh_from_db()
    assert conn.oauth_client_id == ""
    assert GoogleMailActivity.objects.filter(pk=message.pk).exists()


def test_successful_migration_switches_token_without_touching_calendar(
    separate_clients, admin_profile
):
    old = connection(admin_profile, legacy=True)
    calendar = connection(admin_profile, "calendar", legacy=True)
    cache(old)
    started = begin(admin_profile, "gmail")
    with (
        patch(
            "common.google_integration.token_request",
            return_value=token_response("gmail"),
        ),
        patch("common.google_integration.verify_oauth2_token", return_value=IDENTITY),
    ):
        updated = complete(admin_profile, "code", started["state"])
    assert updated.pk == old.pk and independent_disconnect(updated)
    assert not updated.mail_activity.exists()
    calendar.refresh_from_db()
    assert decrypt(calendar.encrypted_refresh_token) == "calendar-refresh"
    assert not calendar.oauth_client_id


@pytest.mark.parametrize("field", ["CLIENT_ID", "PROJECT_ID"])
def test_credentials_changed_during_consent_fail_safely(
    separate_clients, admin_profile, field
):
    conn = connection(admin_profile, legacy=True)
    started = begin(admin_profile, "gmail")
    setattr(separate_clients, f"GOOGLE_GMAIL_{field}", "changed")
    with (
        patch("common.google_integration.requests.post") as post,
        pytest.raises(GoogleError),
    ):
        complete(admin_profile, "code", started["state"])
    post.assert_not_called()
    conn.refresh_from_db()
    assert decrypt(conn.encrypted_refresh_token) == "gmail-refresh"


def test_new_consent_cannot_be_overwritten_by_old_callback(
    separate_clients, admin_profile
):
    started = begin(admin_profile, "gmail")

    def exchange(*args):
        begin(admin_profile, "gmail")
        return token_response("gmail")

    with (
        patch("common.google_integration.token_request", side_effect=exchange),
        patch("common.google_integration.verify_oauth2_token", return_value=IDENTITY),
        pytest.raises(GoogleError, match="Connection changed"),
    ):
        complete(admin_profile, "code", started["state"])
    conn = GoogleConnection.objects.get(profile=admin_profile, service="gmail")
    assert not conn.encrypted_refresh_token and conn.pending_client_id == "gmail-client"


@pytest.mark.parametrize("service", ["gmail", "calendar"])
def test_disconnect_revokes_only_isolated_service(
    separate_clients, admin_client, user_client, admin_profile, user_profile, service
):
    conn = connection(admin_profile, service)
    other = connection(admin_profile, "calendar" if service == "gmail" else "gmail")
    other_user = connection(user_profile, service)
    with patch(
        "common.google_integration.requests.post", return_value=Mock(status_code=200)
    ) as post:
        assert (
            user_client.post(
                "/api/integrations/google/",
                {"service": service, "operation": "disconnect"},
                format="json",
            ).status_code
            == 200
        )
        # User endpoint can only select that user's own connection, never admin's.
        assert GoogleConnection.objects.filter(pk=conn.pk).exists()
        post.reset_mock()
        result = admin_client.post(
            "/api/integrations/google/",
            {"service": service, "operation": "disconnect"},
            format="json",
        )
    assert result.status_code == 200 and result.data == {
        "disconnected": True,
        "revoked": True,
    }
    post.assert_called_once_with(
        "https://oauth2.googleapis.com/revoke",
        data={"token": f"{service}-refresh"},
        timeout=20,
    )
    assert not GoogleConnection.objects.filter(pk=conn.pk).exists()
    assert GoogleConnection.objects.filter(pk=other.pk).exists()
    assert not GoogleConnection.objects.filter(pk=other_user.pk).exists()


@pytest.mark.parametrize("failure", [503, 400, "timeout"])
def test_failed_independent_revocation_preserves_data_for_retry(
    separate_clients, admin_client, admin_profile, failure
):
    conn = connection(admin_profile)
    message = cache(conn)
    kwargs = (
        {"side_effect": requests.Timeout("private detail")}
        if failure == "timeout"
        else {
            "return_value": Mock(
                status_code=failure, json=lambda: {"error": "invalid_request"}
            )
        }
    )
    with patch("common.google_integration.requests.post", **kwargs):
        response = admin_client.post(
            "/api/integrations/google/",
            {"service": "gmail", "operation": "disconnect"},
            format="json",
        )
    assert response.status_code == 400 and "private detail" not in str(response.data)
    assert GoogleConnection.objects.filter(pk=conn.pk).exists()
    assert GoogleMailActivity.objects.filter(pk=message.pk).exists()


def test_shared_revocation_does_not_delete_new_project_connection(
    separate_clients, admin_client, admin_profile
):
    legacy = connection(admin_profile, legacy=True)
    calendar = connection(admin_profile, "calendar")
    with patch(
        "common.google_integration.requests.post", return_value=Mock(status_code=200)
    ):
        response = admin_client.post(
            "/api/integrations/google/",
            {"service": "gmail", "operation": "revoke", "confirm_revoke": True},
            format="json",
        )
    assert response.status_code == 200
    assert not GoogleConnection.objects.filter(pk=legacy.pk).exists()
    assert GoogleConnection.objects.filter(pk=calendar.pk).exists()


def test_legacy_disconnect_stays_local_after_new_clients_configured(
    separate_clients, admin_client, admin_profile
):
    connection(admin_profile, legacy=True)
    calendar = connection(admin_profile, "calendar", legacy=True)
    with patch("common.google_integration.requests.post") as post:
        response = admin_client.post(
            "/api/integrations/google/",
            {"service": "gmail", "operation": "disconnect"},
            format="json",
        )
    post.assert_not_called()
    assert response.data == {"disconnected": True, "revoked": False}
    assert GoogleConnection.objects.filter(pk=calendar.pk).exists()


@pytest.mark.parametrize("other_key", ["legacy", "login", "sender", "calendar"])
def test_shared_or_unknown_project_blocks_new_connection(
    separate_clients, admin_profile, other_key
):
    prefix = PREFIXES[other_key]
    setattr(separate_clients, f"{prefix}_PROJECT_ID", "hdm-gmail")
    assert isolation_errors("gmail")
    assert not configured("gmail")
    assert configured()  # Keep background refresh of existing grants available.
    with (
        pytest.raises(Exception, match="configuration"),
        patch("common.google_integration.requests.post") as post,
    ):
        begin(admin_profile, "gmail")
    post.assert_not_called()
    setattr(separate_clients, f"{prefix}_PROJECT_ID", "")
    assert isolation_errors("gmail")


def test_partial_credentials_do_not_fall_back_to_shared_client(
    separate_clients, admin_profile
):
    separate_clients.GOOGLE_GMAIL_CLIENT_SECRET = ""
    assert not configured("gmail") and configured("calendar")
    assert isolation_errors("gmail")


def test_removed_dedicated_credentials_do_not_destroy_cached_data(
    separate_clients, admin_profile, admin_client
):
    conn = connection(admin_profile)
    message = cache(conn)
    separate_clients.GOOGLE_GMAIL_CLIENT_ID = "rotated-client"
    with (
        pytest.raises(GoogleError),
        patch("common.google_integration.requests.post") as post,
    ):
        GoogleAPI(conn)
    post.assert_not_called()
    response = admin_client.post(
        "/api/integrations/google/",
        {"service": "gmail", "operation": "disconnect"},
        format="json",
    )
    assert response.status_code == 400
    assert GoogleMailActivity.objects.filter(pk=message.pk).exists()


def test_hosted_validation_rejects_shared_project_without_exposing_secrets(
    separate_clients,
):
    separate_clients.GOOGLE_GMAIL_PROJECT_ID = "hdm-calendar"
    with pytest.raises(CommandError) as error:
        validate_settings(separate_clients)
    assert "different Google Cloud project" in str(error.value)
    assert "gmail-secret" not in str(error.value)


@pytest.mark.parametrize("has_token", [True, False])
def test_unusable_independent_connection_can_be_removed_without_claiming_revocation(
    separate_clients, admin_client, admin_profile, has_token
):
    conn = connection(admin_profile)
    other = connection(admin_profile, "calendar")
    message = cache(conn)
    if not has_token:
        conn.encrypted_refresh_token = ""
        conn.save(update_fields=["encrypted_refresh_token"])
    with patch(
        "common.google_integration.requests.post",
        return_value=Mock(status_code=400, json=lambda: {"error": "invalid_token"}),
    ) as post:
        response = admin_client.post(
            "/api/integrations/google/",
            {"service": "gmail", "operation": "disconnect"},
            format="json",
        )
    assert response.status_code == 200
    assert response.data == {"disconnected": True, "revoked": False}
    assert post.call_count == int(has_token)
    assert not GoogleConnection.objects.filter(pk=conn.pk).exists()
    assert not GoogleMailActivity.objects.filter(pk=message.pk).exists()
    assert GoogleConnection.objects.filter(pk=other.pk).exists()


def test_different_declared_projects_cannot_reuse_client_id(separate_clients):
    separate_clients.GOOGLE_GMAIL_CLIENT_ID = separate_clients.GOOGLE_CLIENT_ID
    assert not configured("gmail")
    assert any("own OAuth client" in error for error in isolation_errors("gmail"))
