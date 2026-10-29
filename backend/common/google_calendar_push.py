"""Calendar change hints, authenticated per connection and OAuth generation."""

import logging
import uuid
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from urllib.parse import quote, urlsplit

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone

from common.google_integration import GoogleError
from common.models import GoogleConnection

logger = logging.getLogger(__name__)
TOKEN_SALT = "common.calendar-watch.v1"
WATCH_SECONDS = 7 * 24 * 60 * 60


def push_configured():
    url = urlsplit(settings.GOOGLE_CALENDAR_PUSH_URL)
    return url.scheme == "https" and bool(url.netloc) and not url.username


def channel_token(conn, channel_id):
    return signing.dumps(
        [str(conn.org_id), conn.pk.hex, conn.generation.hex, channel_id],
        salt=TOKEN_SALT,
        compress=True,
    )


def stop_watch(api, channel_id, resource):
    if not channel_id or not resource:
        return
    try:
        api.request(
            "POST",
            "calendar/v3/channels/stop",
            body={"id": channel_id, "resourceId": resource},
        )
    except GoogleError:
        # An expired channel or revoked grant must not block local cleanup.
        logger.warning("Calendar watch could not be stopped")


def renew_watch(conn, api):
    if not push_configured():
        return
    now = timezone.now()
    if (
        conn.calendar_watch_expires_at
        and conn.calendar_watch_expires_at > now + timedelta(days=1)
    ):
        return
    channel_id = uuid.uuid4().hex
    try:
        result = api.request(
            "POST",
            "calendar/v3/calendars/"
            + quote(conn.calendar_id, safe="")
            + "/events/watch",
            body={
                "id": channel_id,
                "type": "web_hook",
                "address": settings.GOOGLE_CALENDAR_PUSH_URL,
                "token": channel_token(conn, channel_id),
                "expiration": str(
                    int((now + timedelta(seconds=WATCH_SECONDS)).timestamp() * 1000)
                ),
            },
        )
        resource = result["resourceId"]
        expires = datetime.fromtimestamp(
            int(result["expiration"]) / 1000, dt_timezone.utc
        )
        if (
            result.get("id") != channel_id
            or not isinstance(resource, str)
            or not resource
            or len(resource) > 1024
            or expires <= now
        ):
            raise ValueError("Invalid watch")
    except (GoogleError, KeyError, ValueError, TypeError, OverflowError):
        logger.warning("Calendar watch renewal failed for connection %s", conn.pk)
        return
    updated = GoogleConnection.objects.filter(
        pk=conn.pk, generation=conn.generation, status="connected"
    ).update(
        calendar_watch_id=channel_id,
        calendar_watch_resource=resource,
        calendar_watch_expires_at=expires,
    )
    if updated:
        stop_watch(api, conn.calendar_watch_id, conn.calendar_watch_resource)
    else:
        stop_watch(api, channel_id, resource)


def reset_calendar_state(conn):
    conn.calendar_sync_token = conn.calendar_watch_id = conn.calendar_watch_resource = (
        ""
    )
    conn.calendar_full_synced_at = conn.calendar_sync_requested_at = (
        conn.calendar_watch_expires_at
    ) = None


def request_calendar_sync(conn):
    """Do not lose changes received while a sync is running or before commit."""
    from common.tasks import sync_google_connection

    with transaction.atomic():
        row = (
            GoogleConnection.objects.select_for_update()
            .filter(
                pk=conn.pk,
                generation=conn.generation,
                status="connected",
                service="calendar",
                profile__is_active=True,
                profile__user__is_active=True,
                org__is_active=True,
                org__closing_at__isnull=True,
            )
            .first()
        )
        if not row:
            return
        pending = bool(row.calendar_sync_requested_at)
        row.calendar_sync_requested_at = timezone.now()
        row.save(update_fields=["calendar_sync_requested_at"])
        if not pending and not row.sync_started_at:

            def enqueue():
                try:
                    sync_google_connection.delay(str(row.org_id), str(row.pk))
                except Exception:
                    # Persist the pending marker; the scheduled fallback retries it.
                    logger.warning(
                        "Calendar sync queue unavailable for connection %s", row.pk
                    )

            transaction.on_commit(enqueue)


def request_host_sync(org_id, host_id):
    for conn in GoogleConnection.objects.filter(
        org_id=org_id, profile_id=host_id, service="calendar", status="connected"
    ):
        request_calendar_sync(conn)
