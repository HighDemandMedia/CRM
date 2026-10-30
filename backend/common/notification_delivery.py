"""Bounded, recipient-scoped delivery batches, independent of the bell history."""

from datetime import timedelta

from django.core import signing
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from common.models import Notification
from common.notification_preferences import delivery_channels, preferences_payload
from common.serializer import NotificationSerializer

SALT = "crm.notification-delivery"


def delivery_batch(profile, cursor=None):
    cutoff = timezone.now() - timedelta(minutes=15)
    after_id = ""
    if cursor:
        try:
            payload = signing.loads(cursor, salt=SALT, max_age=86400)
            if payload["profile"] == str(profile.pk):
                cutoff = max(cutoff, parse_datetime(payload["at"]))
                after_id = payload["id"]
        except (signing.BadSignature, KeyError, TypeError, ValueError):
            pass
    position = Q(created_at__gt=cutoff)
    if after_id:
        position |= Q(created_at=cutoff, id__gt=after_id)
    rows = list(
        Notification.objects.filter(
            recipient=profile,
            org_id=profile.org_id,
        )
        .filter(position)
        .select_related("actor__user")
        .order_by("created_at", "id")[:101]
    )
    batch = rows[:100]
    results = []
    for row in batch:
        channels = delivery_channels(row, profile)
        if not row.read_at and (channels["popup"] or channels["browser"]):
            results.append({**NotificationSerializer(row).data, "channels": channels})
    # Keep the last timestamp when empty: a concurrent uncommitted insert may
    # still arrive with an earlier created_at than this poll's wall clock.
    if batch:
        cutoff, after_id = batch[-1].created_at, str(batch[-1].pk)
    return {
        "deliveries": results,
        "delivery_cursor": signing.dumps(
            {"profile": str(profile.pk), "at": cutoff.isoformat(), "id": after_id},
            salt=SALT,
        ),
        "delivery_profile": str(profile.pk),
        "delivery_preferences": preferences_payload(profile)["values"],
        "delivery_more": len(rows) > 100,
    }
