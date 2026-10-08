"""Bounded background synchronization; page loads read the local cache only."""

import base64
import hashlib
import html
import json
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from email.utils import getaddresses
from html.parser import HTMLParser
from types import SimpleNamespace
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from common.google_integration import GoogleError, encrypt
from common.google_mail import visible_mail_contacts
from common.models import (
    GoogleCalendarEvent,
    GoogleCalendarMirror,
    GoogleConnection,
    GoogleMailActivity,
    SalesAppointment,
)
from common.rbac import calendar_scoped, permitted, require


class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head"):
            self.hidden += 1
        if tag in ("p", "br", "div", "li", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def message_body(api, message_id, payload):
    """Plain text only: never render HTML, tracking pixels, or attachment files."""
    plain, html = [], []

    def walk(part):
        if part.get("filename"):
            return
        mime = part.get("mimeType")
        if mime in ("text/plain", "text/html"):
            body = part.get("body", {})
            data = body.get("data", "")
            if not data and body.get("attachmentId"):
                data = api.get(
                    f"gmail/v1/users/me/messages/{quote(message_id, safe='')}/attachments/{quote(body['attachmentId'], safe='')}"
                ).get("data", "")
            try:
                raw = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
                content_type = next(
                    (
                        h.get("value", "")
                        for h in part.get("headers", [])
                        if h.get("name", "").lower() == "content-type"
                    ),
                    "",
                )
                from email.message import Message

                header = Message()
                header["content-type"] = content_type
                text = raw.decode(
                    header.get_content_charset() or "utf-8", errors="replace"
                )
            except (ValueError, LookupError):
                text = ""
            (plain if mime == "text/plain" else html).append(text)
        for child in part.get("parts", []):
            walk(child)

    walk(payload)
    if plain:
        return "\n".join(plain)
    parser = PlainHTML()
    parser.feed("\n".join(html))
    return "".join(parser.parts).strip()


def sync_gmail(conn, api):
    require(conn.profile, "contacts", "view")
    emails = {
        email.strip().lower()
        for email in visible_mail_contacts(conn.profile)
        .exclude(email__isnull=True)
        .values_list("email", flat=True)
        if email
    }
    # Only retain mail for contacts still visible to this mailbox owner.
    conn.mail_activity.exclude(contact_email__in=emails).delete()
    contacts_fingerprint = hashlib.sha256(
        json.dumps(sorted(emails)).encode()
    ).hexdigest()
    if conn.mail_contacts_fingerprint != contacts_fingerprint:
        # Newly visible/created contacts need historical mail too. Restart the bounded
        # 90-day scan without clearing cached messages; subsequent history catches changes.
        conn.history_id = conn.initial_history_id = conn.mail_page_token = ""
        conn.mail_contacts_fingerprint = contacts_fingerprint
        GoogleConnection.objects.filter(pk=conn.pk, generation=conn.generation).update(
            history_id="",
            initial_history_id="",
            mail_page_token="",
            mail_contacts_fingerprint=contacts_fingerprint,
        )
    baseline = api.get("gmail/v1/users/me/profile")["historyId"]
    ids, deleted = set(), set()
    cursor = conn.history_id
    if cursor:
        try:
            data = api.get(
                "gmail/v1/users/me/history",
                {"startHistoryId": cursor, "maxResults": 50},
            )
            history = data.get("history", [])
            for change in history:
                for key in ("messagesAdded", "labelsAdded", "labelsRemoved"):
                    ids.update(item["message"]["id"] for item in change.get(key, []))
                deleted.update(
                    item["message"]["id"] for item in change.get("messagesDeleted", [])
                )
            # Advance only through the successfully handled page, never past unseen changes.
            baseline = (
                history[-1]["id"]
                if data.get("nextPageToken") and history
                else data.get("historyId", baseline)
            )
        except GoogleError as exc:
            if exc.status != 404:
                raise
            cursor = ""
            conn.mail_activity.all().delete()
            conn.initial_history_id = ""
            conn.mail_page_token = ""
    initial_next = None
    if not cursor:
        # Resume a 50-message page each run; large inboxes cannot monopolize a worker.
        if not conn.initial_history_id:
            conn.initial_history_id = baseline
            GoogleConnection.objects.filter(
                pk=conn.pk, generation=conn.generation
            ).update(initial_history_id=baseline)
        baseline = conn.initial_history_id
        data = api.get(
            "gmail/v1/users/me/messages",
            {
                "q": "newer_than:90d -in:spam -in:trash -in:drafts",
                "maxResults": 50,
                **({"pageToken": conn.mail_page_token} if conn.mail_page_token else {}),
            },
        )
        ids.update(item["id"] for item in data.get("messages", []))
        initial_next = data.get("nextPageToken")
    for message_id in ids - deleted:
        try:
            message = api.get(
                "gmail/v1/users/me/messages/" + quote(message_id, safe=""),
                {
                    "format": "metadata",
                    "metadataHeaders": ["From", "To", "Cc", "Subject", "Reply-To"],
                },
            )
        except GoogleError as exc:
            if exc.status == 404:
                deleted.add(message_id)
                continue
            raise
        labels = set(message.get("labelIds", []))
        if labels.intersection({"TRASH", "SPAM", "DRAFT"}):
            deleted.add(message_id)
            continue
        headers = {
            h["name"].lower(): h["value"]
            for h in message.get("payload", {}).get("headers", [])
        }
        sender = next(
            (
                email.lower()
                for _, email in getaddresses([headers.get("from", "")])
                if email
            ),
            "",
        )
        recipients = [
            email.lower() for _, email in getaddresses([headers.get("to", "")]) if email
        ]
        cc = [
            email.lower() for _, email in getaddresses([headers.get("cc", "")]) if email
        ]
        sent = "SENT" in labels
        matches = (set(recipients + cc) if sent else {sender}) & emails
        if not matches:
            continue
        full = api.get(
            "gmail/v1/users/me/messages/" + quote(message_id, safe=""),
            {"format": "full"},
        )
        body = encrypt(message_body(api, message_id, full.get("payload", {})))
        occurred = datetime.fromtimestamp(
            int(message["internalDate"]) / 1000, tz=dt_timezone.utc
        )
        with transaction.atomic():
            if (
                not GoogleConnection.objects.select_for_update()
                .filter(pk=conn.pk, generation=conn.generation, status="connected")
                .exists()
            ):
                return
            for email in matches:
                GoogleMailActivity.objects.update_or_create(
                    org=conn.org,
                    connection=conn,
                    message_id=message_id,
                    contact_email=email,
                    defaults={
                        "thread_id": message.get("threadId", message_id),
                        "sender": sender[:254],
                        "recipients": recipients,
                        "cc": cc,
                        "reply_to": [
                            email.lower()
                            for _, email in getaddresses([headers.get("reply-to", "")])
                            if email
                        ],
                        "subject": headers.get("subject", "")[:1024],
                        "direction": "sent" if sent else "received",
                        "occurred_at": occurred,
                        "encrypted_body": body,
                    },
                )
    conn.mail_activity.filter(message_id__in=deleted).delete()
    GoogleConnection.objects.filter(pk=conn.pk, generation=conn.generation).update(
        history_id=baseline if not initial_next else "",
        mail_page_token=initial_next or "",
        initial_history_id=baseline if initial_next else "",
    )


def fingerprint(appointment):
    return hashlib.sha256(
        json.dumps(
            [
                appointment.title,
                appointment.internal_notes,
                appointment.starts_at.isoformat(),
                appointment.ends_at.isoformat(),
                bool(appointment.cancelled_at),
            ]
        ).encode()
    ).hexdigest()


def event_times(event, calendar_timezone="UTC"):
    start, end = event.get("start", {}), event.get("end", {})
    if start.get("date") and end.get("date"):
        try:
            zone = ZoneInfo(calendar_timezone)
        except ZoneInfoNotFoundError:
            zone = ZoneInfo("UTC")
        return (
            datetime.fromisoformat(start["date"]).replace(tzinfo=zone),
            datetime.fromisoformat(end["date"]).replace(tzinfo=zone),
            True,
        )
    first, last = (
        parse_datetime(start.get("dateTime", "")),
        parse_datetime(end.get("dateTime", "")),
    )
    if (
        not first
        or not last
        or not timezone.is_aware(first)
        or not timezone.is_aware(last)
        or last <= first
    ):
        raise GoogleError("Google returned an event with invalid dates.")
    return first, last, False


def sync_mirrors(conn, api, base, writable):
    if not writable:
        return
    # Only the connected user's own hosted events are exported; no invite email is sent.
    appointments = calendar_scoped(
        SalesAppointment.objects.filter(
            org=conn.org,
            host=conn.profile,
            starts_at__gte=timezone.now() - timedelta(days=90),
            starts_at__lte=timezone.now() + timedelta(days=365),
        ),
        conn.profile,
    )
    mirrored = conn.mirrors.values_list("appointment_id", flat=True)
    appointments = SalesAppointment.objects.filter(
        Q(pk__in=appointments.values("pk")) | Q(pk__in=mirrored),
        org=conn.org,
        host=conn.profile,
    )
    for appointment_id in appointments.values_list("pk", flat=True):
        snapshot = SalesAppointment.objects.filter(
            pk=appointment_id, org=conn.org
        ).first()
        if not snapshot:
            continue
        previous_mirror = conn.mirrors.filter(appointment_id=appointment_id).first()
        external_id = (
            previous_mirror.external_id
            if previous_mirror
            else "hdm"
            + hashlib.sha256(
                f"{conn.org_id}:{conn.profile_id}:{appointment_id}".encode()
            ).hexdigest()
        )
        path = base + "/events/" + quote(external_id, safe="")
        try:
            remote = api.get(path)
        except GoogleError as exc:
            if exc.status not in (404, 410):
                raise
            remote = None
        write = None
        with transaction.atomic():
            if (
                not GoogleConnection.objects.select_for_update()
                .filter(pk=conn.pk, generation=conn.generation, status="connected")
                .exists()
            ):
                return
            appointment = (
                SalesAppointment.objects.select_for_update()
                .filter(pk=appointment_id, org=conn.org)
                .first()
            )
            if not appointment or fingerprint(appointment) != fingerprint(snapshot):
                continue
            mirror = conn.mirrors.filter(appointment=appointment).first()
            if (mirror.etag if mirror else None) != (
                previous_mirror.etag if previous_mirror else None
            ):
                continue
            if not mirror and appointment.cancelled_at:
                continue
            action = "cancel" if appointment.cancelled_at else "edit"
            if not calendar_scoped(
                SalesAppointment.objects.filter(pk=appointment.pk), conn.profile, action
            ).exists():
                continue
            payload = {
                "summary": appointment.title,
                "description": html.escape(appointment.internal_notes),
                "start": {"dateTime": appointment.starts_at.isoformat()},
                "end": {"dateTime": appointment.ends_at.isoformat()},
            }
            local_changed = mirror and mirror.fingerprint != fingerprint(appointment)
            remote_changed = (
                ((remote.get("etag", "") if remote else "") != mirror.etag)
                if mirror
                else bool(remote)
            )
            if (
                local_changed
                and remote_changed
                and appointment.cancelled_at
                and (not remote or remote.get("status") == "cancelled")
            ):
                local_changed = remote_changed = False
            if (
                local_changed
                and remote_changed
                and remote
                and remote.get("status") != "cancelled"
            ):
                remote_start, remote_end, _ = event_times(remote)
                parser = PlainHTML()
                parser.feed(remote.get("description", ""))
                if (
                    remote.get("summary", ""),
                    "".join(parser.parts).strip(),
                    remote_start,
                    remote_end,
                ) == (
                    appointment.title,
                    appointment.internal_notes,
                    appointment.starts_at,
                    appointment.ends_at,
                ) and not appointment.cancelled_at:
                    local_changed = remote_changed = False
            if local_changed and remote_changed:
                # Do not overwrite either side when both changed since the last sync.
                raise GoogleError(
                    "Calendar conflict: align the event in Google with the CRM (or cancel both), then sync again."
                )
            if remote_changed:
                from common.views.sales_appointment_views import (
                    external_attendees,
                    sync_attendee,
                )

                if any(
                    not permitted(conn.profile, record, "edit")
                    for record in external_attendees(appointment)
                ):
                    raise GoogleError(
                        "Calendar change needs permission to edit the linked CRM records."
                    )
                cancelled = not remote or remote.get("status") == "cancelled"
                if not calendar_scoped(
                    SalesAppointment.objects.filter(pk=appointment.pk),
                    conn.profile,
                    "cancel" if cancelled else "edit",
                ).exists():
                    raise GoogleError(
                        "Your permission set does not allow this Calendar change."
                    )
                previous = appointment.starts_at
                if cancelled:
                    appointment.cancelled_at = timezone.now()
                    appointment.cancelled_by = conn.profile.user
                else:
                    start, end, all_day = event_times(remote)
                    if all_day:
                        raise GoogleError(
                            "Keep linked CRM appointments as timed events in Google Calendar."
                        )
                    appointment.starts_at, appointment.ends_at = start, end
                    appointment.title = (remote.get("summary") or "Google event")[:255]
                    parser = PlainHTML()
                    parser.feed(remote.get("description", ""))
                    appointment.internal_notes = "".join(parser.parts).strip()[:10000]
                appointment.change_history = [
                    *appointment.change_history,
                    {
                        "action": "google_sync",
                        "at": timezone.now().isoformat(),
                        "email": conn.email,
                    },
                ]
                appointment.save()
                sync_attendee(
                    appointment,
                    SimpleNamespace(profile=conn.profile, user=conn.profile.user),
                    "cancelled" if cancelled else "rescheduled",
                    previous,
                )
            elif not mirror or local_changed:
                if appointment.cancelled_at:
                    if remote and remote.get("status") != "cancelled":
                        write = ("DELETE", path, {"etag": remote.get("etag")})
                    remote = {"etag": "", "status": "cancelled"}
                elif not remote:
                    write = (
                        "POST",
                        base + "/events",
                        {"body": {**payload, "id": external_id}},
                    )
                elif local_changed:
                    write = (
                        "PATCH",
                        path,
                        {"body": payload, "etag": remote.get("etag")},
                    )
            if not write:
                save_mirror(conn, appointment, external_id, remote)
        if write:
            method, url, options = write
            result = api.request(method, url, params={"sendUpdates": "none"}, **options)
            with transaction.atomic():
                if (
                    not GoogleConnection.objects.select_for_update()
                    .filter(pk=conn.pk, generation=conn.generation, status="connected")
                    .exists()
                ):
                    return
                if not SalesAppointment.objects.filter(
                    pk=appointment_id, org=conn.org
                ).exists():
                    continue
                # Record exactly what was sent. An edit made during the HTTP
                # request remains different and is picked up by the next sync.
                save_mirror(
                    conn, appointment, external_id, result if method != "DELETE" else {}
                )


def save_mirror(conn, appointment, external_id, remote):
    GoogleCalendarMirror.objects.update_or_create(
        connection=conn,
        appointment=appointment,
        defaults={
            "org": conn.org,
            "external_id": external_id,
            "etag": (remote or {}).get("etag", ""),
            "fingerprint": fingerprint(appointment),
        },
    )


def sync_calendar(conn, api):
    require(conn.profile, "calendar", "view")
    calendar = api.get(
        "calendar/v3/users/me/calendarList/" + quote(conn.calendar_id, safe="")
    )
    writable = calendar.get("accessRole") in ("owner", "writer")
    base = "calendar/v3/calendars/" + quote(conn.calendar_id, safe="")
    sync_mirrors(conn, api, base, writable)
    params = {
        "singleEvents": "true",
        "timeMin": (timezone.now() - timedelta(days=90)).isoformat(),
        "timeMax": (timezone.now() + timedelta(days=365)).isoformat(),
        "maxResults": 2500,
    }
    rows = []
    for _ in range(4):
        data = api.get(base + "/events", params)
        for event in data.get("items", []):
            if event.get("status") == "cancelled":
                continue
            start, end, all_day = event_times(event, calendar.get("timeZone", "UTC"))
            href = event.get("htmlLink", "")
            if not href.startswith(
                "https://www.google.com/calendar/"
            ) and not href.startswith("https://calendar.google.com/"):
                href = ""
            parser = PlainHTML()
            parser.feed(event.get("description", ""))
            rows.append(
                {
                    "description": "".join(parser.parts).strip(),
                    "external_id": event["id"],
                    "title": (event.get("summary") or "Busy")[:1024],
                    "starts_at": start,
                    "ends_at": end,
                    "all_day": all_day,
                    "start_date": event.get("start", {}).get("date", ""),
                    "end_date": event.get("end", {}).get("date", ""),
                    "href": href,
                    "busy": event.get("transparency") != "transparent",
                }
            )
        if not data.get("nextPageToken"):
            break
        params["pageToken"] = data["nextPageToken"]
    else:
        raise GoogleError(
            "Calendar contains more than 10,000 events in the sync window."
        )
    with transaction.atomic():
        if (
            not GoogleConnection.objects.select_for_update()
            .filter(pk=conn.pk, generation=conn.generation, status="connected")
            .exists()
        ):
            return
        ids = []
        for row in rows:
            external_id = row.pop("external_id")
            ids.append(external_id)
            GoogleCalendarEvent.objects.update_or_create(
                connection=conn, org=conn.org, external_id=external_id, defaults=row
            )
        conn.events.exclude(external_id__in=ids).delete()
        GoogleConnection.objects.filter(pk=conn.pk).update(
            calendar_writable=writable,
            calendar_name=calendar.get("summary", "Google Calendar")[:255],
        )
