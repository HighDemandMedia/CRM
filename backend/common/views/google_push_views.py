"""Google change callbacks: authenticate hints before processing tenant data."""

import base64
import binascii
import json
import logging
import uuid

from django.conf import settings
from django.core import signing
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.id_token import verify_oauth2_token
from rest_framework import serializers
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.google_push import push_configured

logger = logging.getLogger(__name__)


class BoundedGoogleRequest(Request):
    def __call__(self, *args, **kwargs):
        kwargs["timeout"] = 10
        return super().__call__(*args, **kwargs)


class GmailNotification(serializers.Serializer):
    emailAddress = serializers.EmailField(max_length=254)
    historyId = serializers.RegexField(r"^[0-9]{1,64}$")


class GmailPushView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser,)

    def post(self, request):
        if not push_configured():
            return Response(status=503)
        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer ") or len(authorization) > 8192:
            return Response(status=401)
        try:
            claims = verify_oauth2_token(
                authorization[7:],
                BoundedGoogleRequest(),
                settings.GOOGLE_GMAIL_PUSH_AUDIENCE,
            )
        except (ValueError, GoogleAuthError):
            return Response(status=401)
        if (
            claims.get("email") != settings.GOOGLE_GMAIL_PUSH_SERVICE_ACCOUNT
            or claims.get("email_verified") is not True
        ):
            return Response(status=403)
        # Authenticate first; refuse another subscription even with a valid Google identity.
        if (
            not isinstance(request.data, dict)
            or request.data.get("subscription")
            != settings.GOOGLE_GMAIL_PUSH_SUBSCRIPTION
        ):
            return Response(status=400)
        try:
            message = request.data["message"]
            data = message["data"]
            if not isinstance(data, str) or len(data) > 4096:
                return Response(status=400)
            payload = json.loads(
                base64.b64decode(
                    data + "=" * (-len(data) % 4), altchars=b"-_", validate=True
                )
            )
        except (KeyError, TypeError, ValueError, binascii.Error):
            return Response(status=400)
        notification = GmailNotification(data=payload)
        notification.is_valid(raise_exception=True)
        from common.tasks import process_gmail_notification

        try:
            process_gmail_notification.delay(
                notification.validated_data["emailAddress"].lower(),
                notification.validated_data["historyId"],
                settings.GOOGLE_GMAIL_PROJECT_ID,
            )
        except Exception:
            # Acknowledge only after durable queueing. Pub/Sub retries a 503.
            logger.error("Gmail push queue unavailable")
            return Response(status=503)
        return Response(status=204)


class CalendarPushView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def post(self, request):
        from common.google_calendar_push import (
            TOKEN_SALT,
            WATCH_SECONDS,
            push_configured,
        )
        from common.tasks import process_calendar_notification

        if not push_configured():
            return Response(status=503)
        token = request.headers.get("X-Goog-Channel-Token", "")
        if not token or len(token) > 256:
            return Response(status=401)
        try:
            org_id, connection_id, generation, channel_id = signing.loads(
                token, salt=TOKEN_SALT, max_age=WATCH_SECONDS
            )
            connection_id = str(uuid.UUID(connection_id))
            generation = str(uuid.UUID(generation))
        except (signing.BadSignature, ValueError, TypeError):
            return Response(status=401)
        resource = request.headers.get("X-Goog-Resource-ID", "")
        state = request.headers.get("X-Goog-Resource-State", "")
        if (
            channel_id != request.headers.get("X-Goog-Channel-ID")
            or not resource
            or len(resource) > 1024
            or state not in ("sync", "exists", "not_exists")
        ):
            return Response(status=400)
        # Google's initial handshake may arrive before watch() returns. The
        # registering task already performs a sync after storing the resource ID.
        if state == "sync":
            return Response(status=204)
        try:
            process_calendar_notification.delay(
                org_id, connection_id, generation, channel_id, resource
            )
        except Exception:
            logger.error("Calendar push queue unavailable")
            return Response(status=503)
        return Response(status=204)
