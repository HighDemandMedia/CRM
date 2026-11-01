"""Durable email delivery for opt-in notification topics, through the CRM provider.

No mailbox connection is needed. Web-form acknowledgements and internal form
emails retain their existing outbox; they must not be delivered twice here.
"""

import logging
import re
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone

from common.links import frontend_url
from common.models import Notification
from common.notification_preferences import channels_for
from common.organization_lifecycle import organization_job

logger = logging.getLogger(__name__)


# Each topic has English and Spanish (title, message, action) variants.
_DEFAULT_COPY = (
    ("New notification", "You have a new notification in the CRM.", "Open CRM"),
    ("Nueva notificación", "Tienes una nueva notificación en el CRM.", "Abrir CRM"),
)
_EMAIL_COPY = {
    "task.reminder": (
        ("Task reminder", "Review your task.", "View task"),
        ("Recordatorio de tarea", "Revisa tu tarea.", "Ver tarea"),
    ),
    "calendar.reminder": (
        ("Upcoming event", "Check your event details.", "View event"),
        ("Próximo evento", "Consulta los detalles de tu evento.", "Ver evento"),
    ),
    "case.mentioned": (
        (
            "You were mentioned in a ticket",
            "Open the ticket to see the mention.",
            "View ticket",
        ),
        (
            "Te mencionaron en un ticket",
            "Abre el ticket para ver la mención.",
            "Ver ticket",
        ),
    ),
    "case.commented": (
        ("New ticket comment", "Open the ticket to read the comment.", "View ticket"),
        (
            "Nuevo comentario en un ticket",
            "Abre el ticket para leer el comentario.",
            "Ver ticket",
        ),
    ),
}


@organization_job
def deliver_notification_emails(org):
    from common.tasks import send_email

    now = timezone.now()
    pending = Notification.objects.filter(org=org, email_pending=True)
    # Do not send stale alerts after an outage, or retry a poison message forever.
    pending.filter(
        Q(created_at__lt=now - timedelta(days=1)) | Q(email_attempts__gte=5)
    ).update(email_pending=False)
    ids = list(
        pending.filter(
            Q(email_attempted_at__isnull=True)
            | Q(email_attempted_at__lte=now - timedelta(minutes=5))
        )
        .order_by("created_at")
        .values_list("pk", flat=True)[:100]
    )
    for notification_id in ids:
        # Claim briefly, matching the web-form outbox: network calls must not
        # hold DB locks. Provider acceptance and DB acknowledgement cannot be
        # atomic; a crash between them can still duplicate a message.
        with transaction.atomic():
            notification = (
                Notification.objects.select_for_update()
                .filter(pk=notification_id, org=org)
                .first()
            )
            if (
                notification is None
                or not notification.email_pending
                or notification.email_attempts >= 5
                or (
                    notification.email_attempted_at
                    and notification.email_attempted_at > now - timedelta(minutes=5)
                )
            ):
                continue
            profile = notification.recipient
            if (
                not profile.is_active
                or profile.removed_at is not None
                or not profile.user.is_active
                or not profile.user.email
                or not channels_for(profile, notification.verb)["email"]
            ):
                notification.email_pending = False
                notification.save(update_fields=["email_pending"])
                continue
            notification.email_attempts += 1
            notification.email_attempted_at = now
            notification.save(update_fields=["email_attempts", "email_attempted_at"])
        spanish = profile.user.ui_language == "es"
        label, message, action = _EMAIL_COPY.get(notification.verb, _DEFAULT_COPY)[
            1 if spanish else 0
        ]
        # Email previews deliberately omit record names and private comments.
        # Opening the CRM rechecks session and record permissions.
        destination = (
            "/calendar"
            if notification.verb == "calendar.reminder"
            else "/tasks"
            if notification.verb == "task.reminder"
            else "/tickets"
        )
        if re.fullmatch(
            r"/(?:tasks|tickets)/[A-Za-z0-9-]+/?|/calendar\?date=\d{4}-\d{2}-\d{2}",
            notification.link,
        ):
            destination = notification.link
        context = {
            "email_language": "es" if spanish else "en",
            "heading": label,
            "message": message,
            "action": action,
            "compact_notification": True,
            "organization": org.name,
            "url": frontend_url(destination),
            "preferences_url": frontend_url("/notifications?tab=preferences"),
        }
        try:
            send_email(
                subject=f"{label} · HDM CRM",
                html_content=render_to_string("notification_email.html", context),
                text_content=f"{label}\n{context['message']}\n{org.name}\n{context['url']}\n{context['preferences_url']}",
                recipients=[profile.user.email],
            )
        except Exception:
            # Avoid logging provider exceptions, which may contain addresses.
            logger.warning(
                "Notification email delivery failed id=%s attempt=%s",
                notification.pk,
                notification.email_attempts,
            )
        else:
            Notification.objects.filter(
                pk=notification.pk, org=org, email_attempted_at=now
            ).update(email_pending=False, email_sent_at=timezone.now())
