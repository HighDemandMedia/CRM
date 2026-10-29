from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from django.utils import timezone

from common.google_sync import sync_calendar_events
from common.models import GoogleAvailabilityCalendar, GoogleConnection
from common.views.sales_appointment_views import google_busy

pytestmark = pytest.mark.django_db


@pytest.fixture
def conn(admin_profile, org_a):
    return GoogleConnection.objects.create(
        org=org_a,
        profile=admin_profile,
        service="calendar",
        status="connected",
        calendar_writable=True,
    )


def event():
    start = timezone.now() + timedelta(days=1)
    return {
        "id": "same-id",
        "summary": "PRIVATE PERSONAL",
        "description": "Private detail",
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": (start + timedelta(hours=1)).isoformat()},
    }


def test_each_calendar_has_separate_cache_and_private_availability(conn, admin_client):
    extra = GoogleAvailabilityCalendar.objects.create(
        org=conn.org, connection=conn, calendar_id="personal"
    )
    api = Mock()
    row = event()
    api.get.return_value = {"items": [row], "nextSyncToken": "main-token"}
    sync_calendar_events(conn, api, conn, {"accessRole": "writer"}, "/primary")
    api.get.return_value = {"items": [row], "nextSyncToken": "personal-token"}
    sync_calendar_events(conn, api, extra, {"accessRole": "reader"}, "/personal")
    assert conn.events.count() == 2
    busy = conn.events.get(calendar_id="personal")
    assert busy.title == "Busy" and not busy.description and not busy.href
    extra.refresh_from_db()
    conn.refresh_from_db()
    assert extra.calendar_sync_token == "personal-token"
    assert conn.calendar_sync_token == "main-token"
    assert (
        google_busy(conn.org, conn.profile_id, busy.starts_at, busy.ends_at).count()
        == 2
    )
    # Clearing the primary calendar must not clear additional availability.
    api.get.return_value = {"items": [], "nextSyncToken": "new-main"}
    conn.calendar_sync_token = ""
    sync_calendar_events(conn, api, conn, {}, "/primary")
    assert list(conn.events.values_list("calendar_id", flat=True)) == ["personal"]
    result = admin_client.get(
        "/api/integrations/google/events/",
        {"start": busy.starts_at.isoformat(), "end": busy.ends_at.isoformat()},
    )
    assert result.status_code == 200, result.data
    assert "PRIVATE PERSONAL" not in str(result.data) and str(busy.pk) not in str(
        result.data
    )


def test_declined_and_transparent_events_do_not_block(conn):
    extra = GoogleAvailabilityCalendar.objects.create(
        org=conn.org, connection=conn, calendar_id="personal"
    )
    row = event()
    api = Mock()
    api.get.return_value = {
        "items": [
            {**row, "attendees": [{"self": True, "responseStatus": "declined"}]},
            {**row, "id": "transparent", "transparency": "transparent"},
        ],
        "nextSyncToken": "next",
    }
    sync_calendar_events(conn, api, extra, {}, "/personal")
    assert not conn.events.filter(busy=True).exists()


def test_calendar_settings_validate_permissions_deduplicate_and_remove_cache(
    conn, admin_client
):
    path = "/api/integrations/google/"

    def meta(url, *args):
        key = url.rsplit("/", 1)[1]
        return {
            "id": key,
            "summary": key,
            "primary": key == "primary",
            "accessRole": "reader" if key == "personal" else "writer",
        }

    with (
        patch("common.views.google_integration_views.GoogleAPI") as factory,
        patch("common.views.google_integration_views.queue"),
    ):
        factory.return_value.get.side_effect = meta
        result = admin_client.post(
            path,
            {
                "service": "calendar",
                "operation": "calendar",
                "calendar_id": "primary",
                "availability_calendar_ids": ["personal", "personal", "primary"],
            },
            format="json",
        )
        assert result.status_code == 200, result.data
        assert list(
            conn.availability_calendars.values_list("calendar_id", flat=True)
        ) == ["personal"]
        result = admin_client.post(
            path,
            {"service": "calendar", "operation": "calendar", "calendar_id": "personal"},
            format="json",
        )
        assert result.status_code == 400
        result = admin_client.post(
            path,
            {
                "service": "calendar",
                "operation": "calendar",
                "calendar_id": "primary",
                "availability_calendar_ids": ["x"] * 11,
            },
            format="json",
        )
        assert result.status_code == 400
        result = admin_client.post(
            path,
            {
                "service": "calendar",
                "operation": "calendar",
                "calendar_id": "primary",
                "availability_calendar_ids": [],
            },
            format="json",
        )
        assert result.status_code == 200
        assert not conn.availability_calendars.exists()


def test_extra_calendar_watch_is_accepted_only_for_its_connection(conn):
    from common.tasks import process_calendar_notification
    from common.testing import restore_rls_context

    extra = GoogleAvailabilityCalendar.objects.create(
        org=conn.org,
        connection=conn,
        calendar_id="personal",
        calendar_watch_id="extra",
        calendar_watch_resource="resource",
        calendar_watch_expires_at=timezone.now() + timedelta(days=1),
    )
    try:
        with patch("common.google_calendar_push.request_calendar_sync") as queue:
            process_calendar_notification(
                str(conn.org_id),
                str(conn.pk),
                str(conn.generation),
                "extra",
                "resource",
            )
            queue.assert_called_once()
            queue.reset_mock()
            process_calendar_notification(
                str(conn.org_id), str(conn.pk), str(conn.generation), "extra", "wrong"
            )
            queue.assert_not_called()
            extra.calendar_watch_expires_at = timezone.now() - timedelta(seconds=1)
            extra.save()
            process_calendar_notification(
                str(conn.org_id),
                str(conn.pk),
                str(conn.generation),
                "extra",
                "resource",
            )
            queue.assert_not_called()
    finally:
        restore_rls_context()
