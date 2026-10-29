"""Appointment notices use the same claim-and-retry pattern as web form emails."""

import logging
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone

from accounts.models import Account
from common.appointment_invitations import calendar_attachment, rsvp_link
from common.links import frontend_url
from common.models import AppointmentEmailDelivery, Profile, SalesAppointment
from common.rbac import calendar_scoped
from contacts.models import Contact

logger = logging.getLogger(__name__)
CLAIM_TIMEOUT = timedelta(minutes=5)


def queue_appointment_emails(
    appointment, action, previous_start=None, previous_end=None
):
    """Persist notices in the caller's transaction; a broker outage cannot lose them."""
    if action not in {"scheduled", "rescheduled", "cancelled"}:
        raise ValueError("Unsupported appointment notice")
    profile_ids = [
        appointment.host_id,
        *appointment.attendee_users.values_list("pk", flat=True),
    ]
    profiles = Profile.objects.filter(
        pk__in=profile_ids,
        org_id=appointment.org_id,
        is_active=True,
        removed_at__isnull=True,
        user__is_active=True,
    ).select_related("user")
    contact_ids = list(appointment.contacts.values_list("pk", flat=True))
    if appointment.contact_id:
        contact_ids.append(appointment.contact_id)
    contacts = Contact.objects.filter(
        pk__in=contact_ids, org_id=appointment.org_id, is_active=True
    )
    company_ids = list(appointment.companies.values_list("pk", flat=True))
    if appointment.company_id:
        company_ids.append(appointment.company_id)
    companies = Account.objects.filter(
        pk__in=company_ids, org_id=appointment.org_id, is_active=True
    )
    recipients = [("profile", p, p.user.email) for p in profiles]
    recipients.extend(("contact", c, c.email) for c in contacts)
    recipients.extend(("company", c, c.email) for c in companies)
    # Native Google invitations own guest delivery; keep the internal host notice.
    if appointment.invitation_provider == "google":
        recipients = [
            r
            for r in recipients
            if r[0] == "profile" and r[1].pk == appointment.host_id
        ]
    payload = {
        "title": appointment.title,
        "organization": appointment.org.name or "High Demand Media CRM",
        "starts_at": appointment.starts_at.isoformat(),
        "ends_at": appointment.ends_at.isoformat(),
        "previous_start": previous_start.isoformat() if previous_start else None,
        "previous_end": previous_end.isoformat() if previous_end else None,
        "timezone": appointment.org.timezone or "UTC",
    }
    seen = set()
    for kind, recipient, email in recipients:
        email = (email or "").strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            continue
        if email in seen:
            continue
        seen.add(email)
        # Same address on a user and contact receives one notice, without listing others.
        row, _ = AppointmentEmailDelivery.objects.get_or_create(
            appointment=appointment,
            revision=len(appointment.change_history),
            email=email,
            defaults={
                "org_id": appointment.org_id,
                "action": action,
                kind: recipient,
                "payload": payload,
            },
        )
        transaction.on_commit(
            lambda pk=str(row.pk), org=str(appointment.org_id): enqueue(pk, org)
        )


def enqueue(delivery_id, org_id):
    from common.tasks import send_appointment_email

    try:
        send_appointment_email.delay(str(delivery_id), str(org_id))
    except Exception as exc:
        # Provider/broker exception text can contain credentials or recipient data.
        logger.warning(
            "Appointment email queued for retry: %s (%s)",
            delivery_id,
            type(exc).__name__,
        )


def _recipient(row):
    appointment = row.appointment
    if row.profile_id:
        profile = row.profile
        if not (
            profile.org_id == row.org_id
            and profile.is_active
            and profile.removed_at is None
            and profile.user.is_active
            and profile.user.email.strip().lower() == row.email
            and (
                appointment.host_id == profile.pk
                or appointment.attendee_users.filter(pk=profile.pk).exists()
            )
            and calendar_scoped(
                SalesAppointment.objects.filter(pk=appointment.pk, org_id=row.org_id),
                profile,
            ).exists()
        ):
            return None
        return (
            profile.user.display_name,
            profile.language or profile.user.ui_language,
            profile.timezone or row.payload["timezone"],
        )
    if row.company_id:
        company = row.company
        if not (
            company.org_id == row.org_id
            and company.is_active
            and (company.email or "").strip().lower() == row.email
            and (
                appointment.company_id == company.pk
                or appointment.companies.filter(pk=company.pk).exists()
            )
        ):
            return None
        return (company.name, "en", row.payload["timezone"])
    contact = row.contact
    if not contact or not (
        contact.org_id == row.org_id
        and contact.is_active
        and (contact.email or "").strip().lower() == row.email
        and (
            appointment.contact_id == contact.pk
            or appointment.contacts.filter(pk=contact.pk).exists()
        )
    ):
        return None
    return (
        contact.name,
        "es" if contact.language in {"es", "Spanish"} else "en",
        row.payload["timezone"],
    )


def _message(row, recipient):
    name, language, zone = recipient
    spanish = language == "es"
    headings = {
        "scheduled": ("Appointment invitation", "Invitación a una cita"),
        "rescheduled": ("Appointment rescheduled", "Cita reprogramada"),
        "cancelled": ("Appointment cancelled", "Cita cancelada"),
    }
    heading = headings[row.action][int(spanish)]
    if row.action == "scheduled" and row.profile_id == row.appointment.host_id:
        heading = "Cita programada" if spanish else "Appointment scheduled"
    try:
        tz = ZoneInfo(zone)
    except (ValueError, KeyError):
        tz, zone = ZoneInfo("UTC"), "UTC"

    def display(value):
        return (
            datetime.fromisoformat(value)
            .astimezone(tz)
            .strftime("%d/%m/%Y · %H:%M" if spanish else "%b %d, %Y · %I:%M %p")
        )

    details = [
        ("Organización" if spanish else "Organization", row.payload["organization"]),
        ("Inicio" if spanish else "Start", display(row.payload["starts_at"])),
        ("Fin" if spanish else "End", display(row.payload["ends_at"])),
        ("Zona horaria" if spanish else "Time zone", zone),
    ]
    if row.action == "rescheduled" and row.payload.get("previous_start"):
        details.append(
            (
                "Inicio anterior" if spanish else "Previous start",
                display(row.payload["previous_start"]),
            )
        )
        if row.payload.get("previous_end"):
            details.append(
                (
                    "Fin anterior" if spanish else "Previous end",
                    display(row.payload["previous_end"]),
                )
            )
    greeting = f"{'Hola' if spanish else 'Hi'} {name},"
    link = frontend_url("/calendar") if row.profile_id else ""
    invite = (
        row.appointment.invitation_provider == "email"
        and row.profile_id != row.appointment.host_id
    )
    respond_link = rsvp_link(row) if invite and row.action != "cancelled" else ""
    html = render_to_string(
        "emails/appointment.html",
        {
            "email_language": "es" if spanish else "en",
            "heading": heading,
            "title": row.payload["title"],
            "greeting": greeting,
            "details": details,
            "link": link,
            "responses": [
                {"label": label, "url": respond_link + "&response=" + value}
                for value, label in [
                    ("accepted", "Aceptar" if spanish else "Accept"),
                    ("tentative", "Quizás" if spanish else "Maybe"),
                    ("declined", "Rechazar" if spanish else "Decline"),
                ]
            ]
            if respond_link
            else [],
            "button_label": "Abrir calendario" if spanish else "Open calendar",
        },
    )
    text = f"{heading}\n\n{greeting}\n{row.payload['title']}\n" + "\n".join(
        f"{label}: {value}" for label, value in details
    )
    if link:
        text += f"\n\n{link}"
    if respond_link:
        text += "\n\n" + ("Responder: " if spanish else "Respond: ") + respond_link
    message = EmailMultiAlternatives(f"{heading} · HDM CRM", text, to=[row.email])
    message.attach_alternative(html, "text/html")
    if invite:
        from email.message import MIMEPart

        content, method = calendar_attachment(row)
        attachment = MIMEPart()
        attachment.set_content(
            content,
            subtype="calendar",
            charset="utf-8",
            params={"method": method},
            disposition="attachment",
            filename="invitation.ics",
        )
        message.attach(attachment)
    return message


def deliver(delivery_id, org_id):
    now = timezone.now()
    with transaction.atomic():
        row = (
            AppointmentEmailDelivery.objects.select_for_update()
            .filter(
                pk=delivery_id,
                org_id=org_id,
                appointment__org_id=org_id,
                completed_at__isnull=True,
                next_attempt_at__lte=now,
            )
            .first()
        )
        if not row or (row.claimed_at and row.claimed_at > now - CLAIM_TIMEOUT):
            return
        newer = AppointmentEmailDelivery.objects.filter(
            appointment_id=row.appointment_id,
            org_id=org_id,
            revision__gt=row.revision,
        ).exists()
        recipient = _recipient(row)
        if newer or not recipient:
            row.completed_at = now
            row.save(update_fields=["completed_at"])
            return
        message = _message(row, recipient)
        claim = uuid4()
        row.claim_id, row.claimed_at = claim, now
        row.attempts += 1
        row.save(update_fields=["claim_id", "claimed_at", "attempts"])
    # Never hold the row lock during network I/O. SMTP cannot guarantee exactly-once
    # after a worker crash between acceptance and acknowledgement, as with web forms.
    try:
        if message.send(fail_silently=False) != 1:
            raise RuntimeError("Mail backend did not accept appointment email")
    except Exception as exc:
        AppointmentEmailDelivery.objects.filter(
            pk=row.pk, org_id=org_id, claim_id=claim
        ).update(
            claim_id=None,
            claimed_at=None,
            next_attempt_at=now
            + timedelta(minutes=min(360, 5 * 2 ** min(row.attempts - 1, 7))),
        )
        logger.warning(
            "Appointment email failed; retry scheduled: %s (%s)",
            row.pk,
            type(exc).__name__,
        )
        # The durable outbox owns retries. Do not let Celery log provider payloads.
        return
    AppointmentEmailDelivery.objects.filter(
        pk=row.pk, org_id=org_id, claim_id=claim
    ).update(
        sent_at=timezone.now(),
        completed_at=timezone.now(),
        claim_id=None,
        claimed_at=None,
    )


def pending_ids(org_id):
    return (
        AppointmentEmailDelivery.objects.filter(
            Q(claimed_at__isnull=True)
            | Q(claimed_at__lte=timezone.now() - CLAIM_TIMEOUT),
            org_id=org_id,
            completed_at__isnull=True,
            next_attempt_at__lte=timezone.now(),
        )
        .order_by("next_attempt_at")
        .values_list("pk", flat=True)[:100]
    )
