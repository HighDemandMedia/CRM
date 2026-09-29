import html
import uuid
from datetime import timedelta
from urllib.parse import quote

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.google_integration import (
    SCOPES,
    GoogleAPI,
    GoogleError,
    begin,
    complete,
    connection_status,
    decrypt,
)
from common.models import GoogleCalendarEvent, GoogleConnection, GoogleMailActivity
from common.permissions import HasOrgContext
from common.rbac import require, scope_for, scoped
from contacts.models import Contact


def own_connection(request, service):
    return get_object_or_404(
        GoogleConnection,
        org=request.profile.org,
        profile=request.profile,
        service=service,
    )


def queue(conn):
    from common.tasks import sync_google_connection

    try:
        sync_google_connection.delay(str(conn.org_id), str(conn.pk))
    except Exception:
        # Scheduled synchronization will retry; no credentials in logs or responses.
        GoogleConnection.objects.filter(pk=conn.pk).update(
            error="Sync could not be queued. It will retry automatically."
        )


class GoogleConnectView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def post(self, request, service):
        if service not in SCOPES:
            raise serializers.ValidationError("Unknown Google service.")
        require(
            request.profile, "contacts" if service == "gmail" else "calendar", "view"
        )
        return Response(begin(request.profile, service))


class GoogleCallbackView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def post(self, request):
        try:
            conn = complete(
                request.profile, request.data.get("code"), request.data.get("state")
            )
        except GoogleError as exc:
            raise serializers.ValidationError(str(exc))
        queue(conn)
        return Response({"connected": True, "service": conn.service})


class GoogleConnectionView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        return Response(connection_status(request.profile))

    def post(self, request):
        service = request.data.get("service")
        conn = own_connection(request, service)
        operation = request.data.get("operation")
        if operation == "disconnect":
            # Delete tokens and cached private data; do not delete events in Google.
            # Do not revoke at Google: doing so also revokes the other service's grant.
            with transaction.atomic():
                GoogleConnection.objects.select_for_update().get(pk=conn.pk).delete()
            return Response({"disconnected": True})
        if conn.status != "connected":
            raise serializers.ValidationError("Connect Google first.")
        if operation == "calendar":
            if service != "calendar":
                raise serializers.ValidationError("Invalid calendar operation.")
            calendar_id = serializers.CharField(max_length=1024).run_validation(
                request.data.get("calendar_id")
            )
            try:
                item = GoogleAPI(conn).get(
                    "calendar/v3/users/me/calendarList/" + quote(calendar_id, safe="")
                )
            except GoogleError as exc:
                raise serializers.ValidationError(str(exc))
            with transaction.atomic():
                conn = GoogleConnection.objects.select_for_update().get(pk=conn.pk)
                if conn.mirrors.exists() and conn.calendar_id != calendar_id:
                    raise serializers.ValidationError(
                        "Disconnect Calendar before switching a calendar with linked CRM appointments."
                    )
                conn.events.all().delete()
                conn.calendar_id, conn.calendar_name = (
                    calendar_id,
                    item.get("summary", "")[:255],
                )
                conn.calendar_writable = item.get("accessRole") in ("owner", "writer")
                conn.generation = uuid.uuid4()
                conn.last_sync = conn.sync_started_at = None
                conn.save()
        elif operation != "sync":
            raise serializers.ValidationError("Unknown operation.")
        queue(conn)
        return Response({"queued": True})


class GoogleCalendarListView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        conn = own_connection(request, "calendar")
        if conn.status != "connected":
            raise serializers.ValidationError("Connect Google Calendar first.")
        try:
            api = GoogleAPI(conn)
            rows, token = [], None
            for _ in range(10):
                data = api.get(
                    "calendar/v3/users/me/calendarList",
                    {"maxResults": 250, **({"pageToken": token} if token else {})},
                )
                rows.extend(
                    {
                        "id": item["id"],
                        "name": item.get("summary", "Calendar"),
                        "writable": item.get("accessRole") in ("owner", "writer"),
                    }
                    for item in data.get("items", [])
                    if not item.get("deleted")
                )
                token = data.get("nextPageToken")
                if not token:
                    return Response({"calendars": rows, "selected": conn.calendar_id})
            raise GoogleError("Too many calendars to list.")
        except GoogleError as exc:
            raise serializers.ValidationError(str(exc))


class GoogleEventsView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        require(request.profile, "calendar", "view")
        field = serializers.DateTimeField()
        start, end = (
            field.run_validation(request.query_params.get("start")),
            field.run_validation(request.query_params.get("end")),
        )
        if end <= start or end - start > timedelta(days=43):
            raise serializers.ValidationError("Invalid calendar range.")
        conn = GoogleConnection.objects.filter(
            org=request.profile.org, profile=request.profile, service="calendar"
        ).first()
        if not conn:
            return Response({"events": [], "status": "disconnected"})
        records = conn.events.filter(
            org=request.profile.org, starts_at__lt=end, ends_at__gt=start
        ).exclude(external_id__in=conn.mirrors.values("external_id"))
        return Response(
            {
                "status": conn.status,
                "last_sync": conn.last_sync,
                "error": conn.error,
                "events": [
                    {
                        "id": "google:" + str(row.pk),
                        "type": "google",
                        "title": row.title,
                        "start": row.starts_at,
                        "end": row.ends_at,
                        "allDay": row.all_day,
                        "startDate": row.start_date,
                        "endDate": row.end_date,
                        "notes": row.description,
                        "href": row.href,
                        "host": conn.email,
                        "canManage": conn.calendar_writable
                        and not row.all_day
                        and conn.status == "connected",
                        "canReschedule": scope_for(request.profile, "calendar", "edit")
                        not in ("none", False),
                        "canCancel": scope_for(request.profile, "calendar", "cancel")
                        not in ("none", False),
                    }
                    for row in records
                ],
            }
        )

    def patch(self, request, pk):
        operation = request.data.get("operation")
        if operation not in ("cancel", "reschedule", "details"):
            raise serializers.ValidationError("Invalid event action.")
        require(
            request.profile, "calendar", "cancel" if operation == "cancel" else "edit"
        )
        event = get_object_or_404(
            GoogleCalendarEvent,
            pk=pk,
            org=request.profile.org,
            connection__profile=request.profile,
            connection__status="connected",
        )
        conn = event.connection
        if (
            not conn.calendar_writable
            or conn.mirrors.filter(external_id=event.external_id).exists()
        ):
            raise serializers.ValidationError(
                "Manage this event through its linked CRM appointment or in Google Calendar."
            )
        path = (
            "calendar/v3/calendars/"
            + quote(conn.calendar_id, safe="")
            + "/events/"
            + quote(event.external_id, safe="")
        )
        try:
            api = GoogleAPI(conn)
            current = api.get(path)
            if operation == "cancel":
                api.request(
                    "DELETE",
                    path,
                    params={"sendUpdates": "none"},
                    etag=current.get("etag"),
                )
                event.delete()
            elif operation == "details":
                title = serializers.CharField(max_length=255).run_validation(
                    request.data.get("title")
                )
                notes = serializers.CharField(
                    max_length=10000, allow_blank=True, trim_whitespace=False
                ).run_validation(request.data.get("internal_notes", ""))
                api.request(
                    "PATCH",
                    path,
                    params={"sendUpdates": "none"},
                    etag=current.get("etag"),
                    body={"summary": title, "description": html.escape(notes)},
                )
                event.title, event.description = title, notes
                event.save(update_fields=["title", "description"])
            else:
                field = serializers.DateTimeField()
                start, end = (
                    field.run_validation(request.data.get("starts_at")),
                    field.run_validation(request.data.get("ends_at")),
                )
                if end <= start or event.all_day:
                    raise serializers.ValidationError(
                        "Choose a valid time range for a timed event."
                    )
                api.request(
                    "PATCH",
                    path,
                    params={"sendUpdates": "none"},
                    etag=current.get("etag"),
                    body={
                        "start": {"dateTime": start.isoformat()},
                        "end": {"dateTime": end.isoformat()},
                    },
                )
                event.starts_at, event.ends_at = start, end
                event.save(update_fields=["starts_at", "ends_at"])
        except GoogleError as exc:
            raise serializers.ValidationError(str(exc))
        queue(conn)
        return Response({"saved": True})


class GoogleMailBodyView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request, pk):
        row = get_object_or_404(
            GoogleMailActivity,
            pk=pk,
            org=request.profile.org,
            connection__profile=request.profile,
        )
        # Access is checked again if record ownership changed after synchronization.
        if not scoped(
            Contact.objects.filter(email__iexact=row.contact_email, is_active=True),
            request.profile,
        ).exists():
            from rest_framework.exceptions import NotFound

            raise NotFound()
        try:
            body = decrypt(row.encrypted_body)
        except GoogleError:
            raise serializers.ValidationError(
                "This email is unavailable. Reconnect Gmail and synchronize again."
            )
        return Response(
            {
                "subject": row.subject,
                "sender": row.sender,
                "recipients": row.recipients,
                "body": body,
                "at": row.occurred_at,
            },
            headers={"Cache-Control": "private, no-store"},
        )


def contact_mail_activity(profile, contact):
    if not contact.email:
        return []
    # Never share personal mailbox content via org-admin privileges.
    rows = (
        GoogleMailActivity.objects.filter(
            org=profile.org,
            connection__profile=profile,
            contact_email=contact.email.strip().lower(),
        )
        .select_related("connection")
        .order_by("-occurred_at")[:100]
    )
    return [
        {
            "id": str(row.pk),
            "subject": row.subject,
            "sender": row.sender,
            "recipients": row.recipients,
            "direction": row.direction,
            "at": row.occurred_at,
            "account": row.connection.email,
            "href": "https://mail.google.com/mail/u/?"
            + "authuser="
            + quote(row.connection.email, safe="")
            + "#all/"
            + quote(row.thread_id, safe=""),
        }
        for row in rows
    ]
