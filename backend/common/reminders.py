"""In-app task and calendar reminders. Beat scans every minute; receipts deduplicate retries."""

from datetime import timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone

from common import notifications
from common.models import (
    GoogleCalendarEvent,
    GoogleCalendarMirror,
    Profile,
    ReminderDelivery,
    SalesAppointment,
)
from common.rbac import calendar_scoped, configured, permitted, scope_for
from tasks.models import Task

CALENDAR_LEAD_MINUTES = 15


def _eligible(profile, org):
    return (
        profile.org_id == org.pk
        and profile.is_active
        and profile.removed_at is None
        and profile.user.is_active
        and profile.notify_in_app
    )


def _deliver(profile, entity, verb, schedule, link, data):
    # Both writes commit together. The unique receipt also serializes concurrent
    # workers; it survives deleting/reading/purging the notification itself.
    with transaction.atomic():
        receipt, created = ReminderDelivery.objects.get_or_create(
            org_id=profile.org_id,
            recipient=profile,
            key=f"{verb}:{entity.pk}:{schedule}",
        )
        if not created:
            return
        notification = notifications.create(
            profile,
            verb,
            entity=entity,
            entity_name=entity.title[:255],
            link=link,
            data=data,
        )
        if notification is None:
            receipt.delete()


def deliver_org_reminders(org, now=None):
    now = now or timezone.now()
    # Tasks have a date, not a time. Start their reminder on the configured day
    # in the organization's timezone, catch up until due, never after due.
    with timezone.override(ZoneInfo(org.timezone or "UTC")):
        today = timezone.localdate(now)
        tasks = (
            Task.objects.filter(
                org=org,
                reminder_days__isnull=False,
                due_date__gte=today,
                due_date__lte=today + timedelta(days=365),
            )
            .exclude(status="Completed")
            .exclude(stage__stage_type="completed")
            .prefetch_related("assigned_to__user", "assigned_to__access_role")
        )
        for task in tasks.iterator(chunk_size=100):
            if today < task.due_date - timedelta(days=task.reminder_days):
                continue
            recipients = list(task.assigned_to.all())
            if not recipients:
                recipients = Profile.objects.filter(
                    org=org, user_id=task.created_by_id
                ).select_related("user", "access_role")
            for profile in recipients:
                if _eligible(profile, org) and permitted(profile, task):
                    _deliver(
                        profile,
                        task,
                        "task.reminder",
                        f"{task.due_date}:{task.reminder_days}",
                        f"/tasks/{task.pk}",
                        {
                            "due_date": task.due_date.isoformat(),
                            "reminder_days": task.reminder_days,
                        },
                    )

        events = (
            SalesAppointment.objects.filter(
                org=org,
                cancelled_at__isnull=True,
                starts_at__gt=now,
                starts_at__lte=now + timedelta(minutes=CALENDAR_LEAD_MINUTES),
            )
            .select_related("host__user", "host__access_role")
            .prefetch_related("attendee_users__user", "attendee_users__access_role")
        )
        for event in events.iterator(chunk_size=100):
            recipients = {p.pk: p for p in [event.host, *event.attendee_users.all()]}
            for profile in recipients.values():
                if (
                    _eligible(profile, org)
                    and calendar_scoped(
                        SalesAppointment.objects.filter(pk=event.pk), profile
                    ).exists()
                ):
                    _calendar_reminder(profile, event)

        # Imported Google events are private to their connected user. Mirrored
        # CRM appointments already get the reminder above; never alert twice.
        mirrors = GoogleCalendarMirror.objects.filter(
            org=org,
            connection_id=OuterRef("connection_id"),
            external_id=OuterRef("external_id"),
        )
        google_events = (
            GoogleCalendarEvent.objects.filter(
                org=org,
                connection__org=org,
                connection__service="calendar",
                connection__status="connected",
                starts_at__gt=now,
                starts_at__lte=now + timedelta(minutes=CALENDAR_LEAD_MINUTES),
                all_day=False,
            )
            .alias(mirrored=Exists(mirrors))
            .filter(mirrored=False)
            .select_related(
                "connection__profile__user", "connection__profile__access_role"
            )
        )
        for event in google_events.iterator(chunk_size=100):
            profile = event.connection.profile
            if _eligible(profile, org) and (
                not configured(profile)
                or scope_for(profile, "calendar", "view") != "none"
            ):
                _calendar_reminder(profile, event)


def _calendar_reminder(profile, event):
    date = timezone.localdate(event.starts_at).isoformat()
    _deliver(
        profile,
        event,
        "calendar.reminder",
        event.starts_at.isoformat(),
        f"/calendar?date={date}",
        {
            "starts_at": event.starts_at.isoformat(),
            "reminder_minutes": CALENDAR_LEAD_MINUTES,
        },
    )
