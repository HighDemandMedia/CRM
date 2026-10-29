"""Authenticated Gmail change hints; the existing sync remains the source of truth."""

import logging
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from common.google_integration import GoogleError
from common.models import GoogleConnection

logger = logging.getLogger(__name__)


def push_configured():
    project = settings.GOOGLE_GMAIL_PROJECT_ID
    return bool(
        project
        and settings.GOOGLE_GMAIL_PUSH_TOPIC.startswith(f"projects/{project}/topics/")
        and settings.GOOGLE_GMAIL_PUSH_SUBSCRIPTION.startswith(
            f"projects/{project}/subscriptions/"
        )
        and settings.GOOGLE_GMAIL_PUSH_AUDIENCE
        and settings.GOOGLE_GMAIL_PUSH_SERVICE_ACCOUNT
    )


def renew_watch(conn, api):
    """Watch the entire mailbox (including sent/archive), renew daily, never reset history."""
    if (
        not push_configured()
        or conn.oauth_project_id != settings.GOOGLE_GMAIL_PROJECT_ID
    ):
        return
    now = timezone.now()
    topic = settings.GOOGLE_GMAIL_PUSH_TOPIC
    if (
        conn.mail_watch_topic == topic
        and conn.mail_watch_expires_at
        and conn.mail_watch_expires_at > now + timedelta(hours=1)
        and conn.mail_watch_renewed_at
        and conn.mail_watch_renewed_at > now - timedelta(days=1)
    ):
        return
    try:
        result = api.request(
            "POST", "gmail/v1/users/me/watch", body={"topicName": topic}
        )
        expires = datetime.fromtimestamp(
            int(result["expiration"]) / 1000, dt_timezone.utc
        )
        if expires <= now:
            raise ValueError("Expired watch")
    except (GoogleError, KeyError, ValueError, TypeError, OverflowError):
        # Push infrastructure failures must not disable the working polling fallback.
        logger.warning("Gmail watch renewal failed for connection %s", conn.pk)
        return
    GoogleConnection.objects.filter(
        pk=conn.pk, generation=conn.generation, status="connected"
    ).update(
        mail_watch_expires_at=expires, mail_watch_renewed_at=now, mail_watch_topic=topic
    )


def request_mail_sync(conn, history_id):
    """Coalesce duplicates and retain a wakeup that arrives during an in-flight sync."""
    from common.tasks import sync_google_connection

    with transaction.atomic():
        row = (
            GoogleConnection.objects.select_for_update()
            .filter(pk=conn.pk, generation=conn.generation, status="connected")
            .first()
        )
        if not row or (row.history_id and int(row.history_id) >= int(history_id)):
            return
        pending = bool(row.mail_sync_requested_at)
        row.mail_sync_requested_at = timezone.now()
        row.save(update_fields=["mail_sync_requested_at"])
        if not pending and not row.sync_started_at:

            def enqueue():
                try:
                    sync_google_connection.delay(str(row.org_id), str(row.pk))
                except Exception:
                    # Allow the notification task's retry to enqueue again. Do not
                    # clear a newer notification or a different connection generation.
                    GoogleConnection.objects.filter(
                        pk=row.pk,
                        generation=row.generation,
                        mail_sync_requested_at=row.mail_sync_requested_at,
                    ).update(mail_sync_requested_at=None)
                    raise

            transaction.on_commit(enqueue)
