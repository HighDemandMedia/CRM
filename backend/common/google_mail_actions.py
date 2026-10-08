"""Explicit user-initiated Gmail actions. No system-sender credentials are used."""

import base64
import hashlib
import json
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from urllib.parse import quote

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import APIException

from accounts.models import Account
from common.google_integration import GMAIL_SEND_SCOPE, GoogleAPI, GoogleError, encrypt
from common.google_mail import mail_rows, record_contacts, visible_mail_contacts
from common.models import (
    Comment,
    GoogleConnection,
    GoogleMailActivity,
    GoogleMailSendOperation,
)
from common.rbac import require_record


class ActionError(APIException):
    status_code = 409


class MailAction(serializers.Serializer):
    action = serializers.ChoiceField(choices=["send", "reply", "forward", "comment"])
    request_id = serializers.UUIDField(required=False)
    message = serializers.UUIDField(required=False)
    to = serializers.ListField(
        child=serializers.EmailField(), max_length=25, required=False
    )
    cc = serializers.ListField(
        child=serializers.EmailField(), max_length=25, required=False, default=list
    )
    subject = serializers.CharField(max_length=998, required=False, allow_blank=True)
    body = serializers.CharField(max_length=100000, trim_whitespace=False)

    def validate(self, data):
        if not data["body"].strip():
            raise serializers.ValidationError("Write a message first.")
        if data["action"] != "comment":
            if not data.get("to") or not data.get("request_id"):
                raise serializers.ValidationError(
                    "Recipients and request ID are required."
                )
            if len(data["to"]) + len(data["cc"]) > 25:
                raise serializers.ValidationError("Use at most 25 recipients.")
            if any(char in data.get("subject", "") for char in "\r\n"):
                raise serializers.ValidationError("Use a single-line subject.")
        if data["action"] != "send" and not data.get("message"):
            raise serializers.ValidationError("Choose an email first.")
        return data


def perform_mail_action(profile, kind, pk, data):
    contacts = record_contacts(profile, kind, pk)
    record = (
        contacts.get(pk=pk)
        if kind == "contact"
        else Account.objects.get(pk=pk, org=profile.org)
    )
    require_record(profile, record, "notes" if data["action"] == "comment" else "edit")
    original = (
        get_object_or_404(mail_rows(profile, contacts), pk=data["message"])
        if data.get("message")
        else None
    )
    if data["action"] == "comment":
        if len(data["body"]) > 8000:
            raise serializers.ValidationError(
                "Keep internal comments under 8000 characters."
            )
        with transaction.atomic():
            note = Comment.objects.create(
                org=profile.org,
                content_type=ContentType.objects.get_for_model(record),
                object_id=record.pk,
                commented_by=profile,
                is_internal=True,
                comment=f"Email: {original.subject or '(No subject)'}\n{data['body']}",
            )
        return {"commented": True, "id": str(note.pk)}
    conn = get_object_or_404(
        GoogleConnection, org=profile.org, profile=profile, service="gmail"
    )
    if conn.status != "connected" or GMAIL_SEND_SCOPE not in conn.scopes:
        raise ActionError(
            "Reconnect Gmail in Profile → Integrations to enable sending."
        )
    digest = hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()
    operation, created = GoogleMailSendOperation.objects.get_or_create(
        connection=conn,
        request_id=data["request_id"],
        defaults={"payload_digest": digest},
    )
    if not created:
        if operation.payload_digest != digest:
            raise ActionError("This request was already used for a different message.")
        if operation.status == "sent":
            return {"sent": True, "id": operation.message_id}
        raise ActionError(
            "Sending is pending or could not be confirmed. Check Gmail Sent before trying again."
        )
    try:
        api = GoogleAPI(conn)
        mime = EmailMessage()
        mime["From"] = conn.email
        mime["To"] = ", ".join(data["to"])
        if data["cc"]:
            mime["Cc"] = ", ".join(data["cc"])
        subject = data.get("subject", "")
        if data["action"] == "reply":
            remote = api.get(
                "gmail/v1/users/me/messages/" + quote(original.message_id, safe=""),
                {"format": "metadata"},
            )
            headers = {
                h["name"].lower(): h["value"]
                for h in remote.get("payload", {}).get("headers", [])
            }
            parent_id = headers.get("message-id", "")
            if not parent_id or any(c in parent_id for c in "\r\n"):
                raise serializers.ValidationError(
                    "The original email cannot be threaded. Open it in Gmail to reply."
                )
            mime["In-Reply-To"] = parent_id
            references = (
                headers.get("references", "").replace("\r", "").replace("\n", " ")
            )
            mime["References"] = " ".join([*references.split()[-20:], parent_id])
            subject = original.subject
        mime["Subject"] = subject
        mime["Date"] = format_datetime(timezone.now())
        mime["Message-ID"] = make_msgid()
        mime.set_content(data["body"])
        payload = {"raw": base64.urlsafe_b64encode(mime.as_bytes()).decode()}
        if data["action"] == "reply":
            payload["threadId"] = original.thread_id
    except (GoogleError, serializers.ValidationError, ValueError):
        operation.status = "failed"
        operation.save(update_fields=["status"])
        raise ActionError(
            "Could not prepare this email. Check Gmail permissions and try a new draft."
        ) from None
    try:
        if not GoogleConnection.objects.filter(
            pk=conn.pk, generation=conn.generation, status="connected"
        ).exists():
            raise GoogleError()
        sent = api.request("POST", "gmail/v1/users/me/messages/send", body=payload)
        if not sent.get("id"):
            raise GoogleError()
    except GoogleError:
        # Never automatically retry an uncertain send: Google may have accepted it.
        operation.status = "unknown"
        operation.save(update_fields=["status"])
        raise ActionError(
            "Sending could not be confirmed. Check Gmail Sent before trying again."
        ) from None
    operation.status, operation.message_id = "sent", sent["id"]
    operation.save(update_fields=["status", "message_id"])
    recipients = {email.lower() for email in data["to"] + data["cc"]}
    matched = {
        email.strip().lower()
        for email in visible_mail_contacts(profile)
        .exclude(email__isnull=True)
        .values_list("email", flat=True)
    } & recipients
    with transaction.atomic():
        # A reconnected mailbox must never inherit cached messages from the old grant.
        if (
            not GoogleConnection.objects.select_for_update()
            .filter(pk=conn.pk, generation=conn.generation, status="connected")
            .exists()
        ):
            return {"sent": True, "id": sent["id"]}
        for email in matched:
            GoogleMailActivity.objects.update_or_create(
                org=profile.org,
                connection=conn,
                contact_email=email,
                message_id=sent["id"],
                defaults={
                    "thread_id": sent.get("threadId", sent["id"]),
                    "sender": conn.email,
                    "recipients": data["to"],
                    "cc": data["cc"],
                    "subject": subject,
                    "direction": "sent",
                    "occurred_at": timezone.now(),
                    "encrypted_body": encrypt(data["body"]),
                },
            )
    return {"sent": True, "id": sent["id"]}
