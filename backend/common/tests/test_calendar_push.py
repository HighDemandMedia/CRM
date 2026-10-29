import uuid
from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from django.db import transaction
from django.utils import timezone
from rest_framework.test import APIClient

from common.google_calendar_push import (
    channel_token,
    renew_watch,
    request_calendar_sync,
)
from common.google_integration import GoogleError
from common.google_sync import sync_calendar
from common.models import GoogleCalendarEvent, GoogleConnection, SalesAppointment
from common.tasks import process_calendar_notification, sync_google_connection

pytestmark = pytest.mark.django_db
PATH = "/api/integrations/google/calendar/push/"


@pytest.fixture(autouse=True)
def push_settings(settings):
    settings.GOOGLE_CALENDAR_PUSH_URL = "https://api.example.com" + PATH


@pytest.fixture
def conn(admin_profile, org_a):
    return GoogleConnection.objects.create(
        org=org_a,
        profile=admin_profile,
        service="calendar",
        status="connected",
        calendar_watch_id=uuid.uuid4().hex,
        calendar_watch_resource="resource",
        calendar_watch_expires_at=timezone.now() + timedelta(days=6),
    )


def headers(conn):
    return {
        "HTTP_X_GOOG_CHANNEL_ID": conn.calendar_watch_id,
        "HTTP_X_GOOG_CHANNEL_TOKEN": channel_token(conn, conn.calendar_watch_id),
        "HTTP_X_GOOG_RESOURCE_ID": conn.calendar_watch_resource,
        "HTTP_X_GOOG_RESOURCE_STATE": "exists",
    }


def test_signed_callback_and_initial_handshake(conn):
    client = APIClient()
    values = headers(conn)
    assert len(values["HTTP_X_GOOG_CHANNEL_TOKEN"]) <= 256
    with patch("common.tasks.process_calendar_notification.delay") as queue:
        assert client.post(PATH).status_code == 401
        assert (
            client.post(
                PATH, **{**values, "HTTP_X_GOOG_CHANNEL_TOKEN": "bad"}
            ).status_code
            == 401
        )
        assert (
            client.post(
                PATH, **{**values, "HTTP_X_GOOG_CHANNEL_ID": "other"}
            ).status_code
            == 400
        )
        assert (
            client.post(
                PATH, **{**values, "HTTP_X_GOOG_RESOURCE_STATE": "sync"}
            ).status_code
            == 204
        )
        queue.assert_not_called()
        assert client.post(PATH, **values).status_code == 204
        queue.assert_called_once_with(
            str(conn.org_id),
            str(conn.pk),
            str(conn.generation),
            conn.calendar_watch_id,
            "resource",
        )
        queue.side_effect = RuntimeError
        assert client.post(PATH, **values).status_code == 503


def test_expired_token_rejected(conn):
    values = headers(conn)
    with patch(
        "django.core.signing.time.time",
        return_value=timezone.now().timestamp() + 8 * 86400,
    ):
        assert APIClient().post(PATH, **values).status_code == 401


@pytest.mark.parametrize(
    "change",
    [
        "tenant",
        "generation",
        "resource",
        "expired",
        "disconnected",
        "closed",
        "inactive",
    ],
)
def test_worker_rejects_stale_or_foreign_channel(conn, org_b, change):
    args = [
        str(conn.org_id),
        str(conn.pk),
        str(conn.generation),
        conn.calendar_watch_id,
        "resource",
    ]
    if change == "tenant":
        args[0] = str(org_b.pk)
    elif change == "generation":
        args[2] = str(uuid.uuid4())
    elif change == "resource":
        args[4] = "other"
    elif change == "expired":
        conn.calendar_watch_expires_at = timezone.now() - timedelta(seconds=1)
        conn.save()
    elif change == "disconnected":
        conn.delete()
    elif change == "closed":
        conn.org.closing_at = timezone.now()
        conn.org.save()
    else:
        conn.profile.is_active = False
        conn.profile.save()
    with patch("common.google_calendar_push.request_calendar_sync") as request:
        process_calendar_notification(*args)
        request.assert_not_called()


def test_valid_worker_and_coalescing(conn, django_capture_on_commit_callbacks):
    with (
        patch("common.tasks.sync_google_connection.delay") as queue,
        django_capture_on_commit_callbacks(execute=True),
    ):
        for _ in range(3):
            process_calendar_notification(
                str(conn.org_id),
                str(conn.pk),
                str(conn.generation),
                conn.calendar_watch_id,
                "resource",
            )
    queue.assert_called_once_with(str(conn.org_id), str(conn.pk))
    conn.refresh_from_db()
    assert conn.calendar_sync_requested_at


def test_busy_connection_retains_pending_change(
    conn, django_capture_on_commit_callbacks
):
    conn.sync_started_at = timezone.now()
    conn.save()
    with (
        patch("common.tasks.sync_google_connection.delay") as queue,
        django_capture_on_commit_callbacks(execute=True),
    ):
        request_calendar_sync(conn)
    queue.assert_not_called()
    conn.refresh_from_db()
    assert conn.calendar_sync_requested_at


def test_renew_watch_only_when_due_and_retire_old_channel(conn, settings):
    api = Mock()
    renew_watch(conn, api)
    api.request.assert_not_called()
    conn.calendar_watch_expires_at = timezone.now()
    conn.save()
    old_id = conn.calendar_watch_id

    def response(method, path, *, body):
        if path.endswith("/watch"):
            assert body["type"] == "web_hook"
            assert len(body["token"]) <= 256
            return {
                "id": body["id"],
                "resourceId": "new-resource",
                "expiration": body["expiration"],
            }
        return {}

    api.request.side_effect = response
    renew_watch(conn, api)
    conn.refresh_from_db()
    assert conn.calendar_watch_id != old_id
    assert conn.calendar_watch_resource == "new-resource"
    api.request.assert_any_call(
        "POST",
        "calendar/v3/channels/stop",
        body={"id": old_id, "resourceId": "resource"},
    )
    settings.GOOGLE_CALENDAR_PUSH_URL = ""
    api.reset_mock()
    renew_watch(conn, api)
    api.request.assert_not_called()


def test_watch_failure_keeps_previous_channel(conn):
    conn.calendar_watch_expires_at = timezone.now()
    conn.save()
    api = Mock()
    api.request.side_effect = GoogleError()
    old_id = conn.calendar_watch_id
    renew_watch(conn, api)
    conn.refresh_from_db()
    assert conn.calendar_watch_id == old_id


def make_appointment(conn):
    return SalesAppointment.objects.create(
        org=conn.org,
        host=conn.profile,
        created_by=conn.profile.user,
        title="Meeting",
        starts_at=timezone.now() + timedelta(days=1),
        ends_at=timezone.now() + timedelta(days=1, hours=1),
    )


def test_appointment_changes_enqueue_after_commit_and_not_on_rollback(
    conn, django_capture_on_commit_callbacks
):
    with patch("common.google_calendar_push.request_host_sync") as request:
        with django_capture_on_commit_callbacks(execute=True):
            event = make_appointment(conn)
            request.assert_not_called()
        request.assert_called_once_with(conn.org_id, conn.profile_id)
        request.reset_mock()
        with django_capture_on_commit_callbacks(execute=True):
            try:
                with transaction.atomic():
                    event.title = "Rolled back"
                    event.save()
                    raise ValueError
            except ValueError:
                pass
        request.assert_not_called()
        with django_capture_on_commit_callbacks(execute=True):
            event._from_google_sync = True
            event.save()
        request.assert_not_called()


def test_notification_during_sync_requests_followup(conn):
    def incoming(*args):
        request_calendar_sync(conn)

    with (
        patch("common.google_integration.GoogleAPI"),
        patch("common.google_calendar_push.renew_watch"),
        patch("common.google_sync.sync_calendar", side_effect=incoming),
        patch.object(sync_google_connection, "apply_async") as queue,
    ):
        sync_google_connection(str(conn.org_id), str(conn.pk))
    queue.assert_called_once_with(args=[str(conn.org_id), str(conn.pk)], countdown=5)
    conn.refresh_from_db()
    assert conn.calendar_sync_requested_at
    assert conn.last_sync and not conn.sync_started_at


def event_data(event_id):
    return {
        "id": event_id,
        "summary": event_id,
        "start": {"dateTime": (timezone.now() + timedelta(days=1)).isoformat()},
        "end": {"dateTime": (timezone.now() + timedelta(days=1, hours=1)).isoformat()},
    }


def seed_cache(conn):
    conn.calendar_sync_token = "previous"
    conn.calendar_full_synced_at = timezone.now()
    conn.save()
    for key in ("keep", "remove"):
        GoogleCalendarEvent.objects.create(
            connection=conn,
            org=conn.org,
            external_id=key,
            title=key,
            starts_at=timezone.now(),
            ends_at=timezone.now() + timedelta(hours=1),
        )


def test_incremental_sync_preserves_unchanged_events_and_removes_cancelled(conn):
    seed_cache(conn)
    api = Mock()
    api.get.side_effect = [
        {"accessRole": "reader", "timeZone": "UTC"},
        {
            "items": [event_data("new"), {"id": "remove", "status": "cancelled"}],
            "nextSyncToken": "next",
        },
    ]
    with patch("common.google_sync.sync_mirrors"):
        sync_calendar(conn, api)
    assert set(conn.events.values_list("external_id", flat=True)) == {"keep", "new"}
    params = api.get.call_args.args[1]
    assert params["syncToken"] == "previous" and "timeMin" not in params
    conn.refresh_from_db()
    assert conn.calendar_sync_token == "next"


def test_expired_sync_token_rebuilds_without_losing_cache_on_failure(conn):
    seed_cache(conn)
    api = Mock()
    api.get.side_effect = [
        {"accessRole": "reader"},
        GoogleError(status=410),
        GoogleError(),
    ]
    with patch("common.google_sync.sync_mirrors"), pytest.raises(GoogleError):
        sync_calendar(conn, api)
    assert conn.events.count() == 2
    conn.refresh_from_db()
    assert conn.calendar_sync_token == "previous"


def test_daily_full_sync_replaces_cache_and_advances_window(conn):
    seed_cache(conn)
    conn.calendar_full_synced_at -= timedelta(days=2)
    conn.save()
    api = Mock()
    api.get.side_effect = [
        {"accessRole": "reader", "timeZone": "UTC"},
        {"items": [event_data("new")], "nextSyncToken": "next"},
    ]
    with patch("common.google_sync.sync_mirrors"):
        sync_calendar(conn, api)
    assert list(conn.events.values_list("external_id", flat=True)) == ["new"]
    params = api.get.call_args.args[1]
    assert "timeMin" in params and "syncToken" not in params


def test_status_endpoint_is_private_and_requires_calendar_permission(
    conn, admin_client, user_client
):
    path = "/api/integrations/google/events/?view=status"
    response = admin_client.get(path)
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    assert str(conn.generation) in response.data["revision"]
    other = user_client.get(path)
    assert other.status_code in (200, 403)
    if other.status_code == 200:
        assert other.data["revision"] == "disconnected"
