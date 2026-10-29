"""Guest invitations and responses, independent from private CRM meeting notes."""

from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from email.utils import parseaddr
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import timezone

from common.links import frontend_url

RESPONSE_LABELS = {
    "needsAction": "Pending",
    "accepted": "Accepted",
    "tentative": "Maybe",
    "declined": "Declined",
}
TOKEN_SALT = "common.appointment-rsvp.v1"


def guests(appointment):
    """Deduplicate addresses and never invite the organizer to their own event."""
    from common.views.sales_appointment_views import external_attendees

    records = [
        (p.user.email, p.user.display_name)
        for p in appointment.attendee_users.filter(
            org_id=appointment.org_id, is_active=True, user__is_active=True
        )
    ]
    records += [
        (r.email, r.name) for r in external_attendees(appointment) if r.is_active
    ]
    host_email = appointment.host.user.email.strip().lower()
    result = {}
    for email, name in records:
        email = (email or "").strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            continue
        if email != host_email:
            result[email] = {"email": email, "displayName": name or email}
    return result


def response_for(appointment, email):
    if not appointment.invitation_provider or not email:
        return ""
    if email.strip().lower() == appointment.host.user.email.strip().lower():
        return ""
    return appointment.guest_responses.get(email.strip().lower(), "needsAction")


def update_google_responses(appointment, remote):
    allowed = guests(appointment)
    responses = dict(appointment.guest_responses)
    for guest in remote.get("attendees", []):
        email = guest.get("email", "").lower()
        status = guest.get("responseStatus", "needsAction")
        if email in allowed and status in RESPONSE_LABELS:
            responses[email] = status
    if responses != appointment.guest_responses:
        appointment.guest_responses = responses
        type(appointment).objects.filter(
            pk=appointment.pk, org_id=appointment.org_id
        ).update(guest_responses=responses)


def rsvp_link(row):
    token = signing.dumps(
        [
            str(row.org_id),
            str(row.appointment_id),
            row.email,
            row.payload["starts_at"],
            row.payload["ends_at"],
        ],
        salt=TOKEN_SALT,
        compress=True,
    )
    return frontend_url("/appointment-response?") + urlencode({"token": token})


def calendar_attachment(row):
    """RFC 5545/5546: stable UID + monotonic sequence for updates/cancellation."""
    method = "CANCEL" if row.action == "cancelled" else "REQUEST"
    organizer = parseaddr(settings.DEFAULT_FROM_EMAIL)[1]
    validate_email(organizer)

    def escape(value):
        return (
            str(value)
            .replace("\\", "\\\\")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .replace("\n", "\\n")
            .replace(";", "\\;")
            .replace(",", "\\,")
        )

    def stamp(value):
        return (
            datetime.fromisoformat(value)
            .astimezone(dt_timezone.utc)
            .strftime("%Y%m%dT%H%M%SZ")
        )

    lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//High Demand Media//CRM//EN",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        f"METHOD:{method}",
        "BEGIN:VEVENT",
        f"UID:{row.appointment_id}@crm.highdemandmedia.com",
        f"SEQUENCE:{row.revision}",
        "DTSTAMP:"
        + timezone.now().astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "DTSTART:" + stamp(row.payload["starts_at"]),
        "DTEND:" + stamp(row.payload["ends_at"]),
        "SUMMARY:" + escape(row.payload["title"]),
        f"ORGANIZER:mailto:{organizer}",
        f"ATTENDEE;RSVP=TRUE;PARTSTAT=NEEDS-ACTION:mailto:{row.email}",
        "STATUS:CANCELLED" if method == "CANCEL" else "STATUS:CONFIRMED",
    ]
    if method == "REQUEST":
        lines.append(
            "DESCRIPTION:" + escape("Respond to this invitation: " + rsvp_link(row))
        )
        lines.append("URL:" + rsvp_link(row))
    lines += ["END:VEVENT", "END:VCALENDAR"]
    # Fold UTF-8 at 75 octets without splitting a code point.
    folded = []
    for line in lines:
        chunk = ""
        for char in line:
            if len((chunk + char).encode("utf-8")) > 75:
                folded.append(chunk)
                chunk = " "
            chunk += char
        folded.append(chunk)
    return "\r\n".join(folded) + "\r\n", method


def read_token(token):
    if not isinstance(token, str) or len(token) > 2048:
        raise signing.BadSignature("Invalid invitation")
    values = signing.loads(token, salt=TOKEN_SALT, max_age=400 * 86400)
    if (
        not isinstance(values, list)
        or len(values) != 5
        or not all(isinstance(v, str) for v in values)
    ):
        raise signing.BadSignature("Invalid invitation")
    return values


def can_respond(appointment, email, start, end):
    return (
        appointment.invitation_provider == "email"
        and not appointment.cancelled_at
        and appointment.org.is_active
        and not appointment.org.closing_at
        and appointment.ends_at + timedelta(days=1) > timezone.now()
        and appointment.starts_at.isoformat() == start
        and appointment.ends_at.isoformat() == end
        and email in guests(appointment)
    )
