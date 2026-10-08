"""Google OAuth and API calls. Credentials never leave the backend."""

import base64
import hashlib
import secrets
from datetime import timedelta
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.id_token import verify_oauth2_token
from rest_framework.exceptions import ValidationError

from common.models import GoogleConnection

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"

SCOPES = {
    "gmail": ["https://www.googleapis.com/auth/gmail.readonly", GMAIL_SEND_SCOPE],
    "calendar": [
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
    ],
}
IDENTITY_SCOPES = ["openid", "https://www.googleapis.com/auth/userinfo.email"]


class GoogleError(Exception):
    def __init__(
        self,
        message="Google is unavailable. Try syncing again later.",
        reconnect=False,
        status=0,
    ):
        super().__init__(message)
        self.reconnect = reconnect
        self.status = status


def configured():
    try:
        cipher()
    except (ValueError, TypeError):
        return False
    return bool(
        settings.GOOGLE_INTEGRATION_CLIENT_ID
        and settings.GOOGLE_INTEGRATION_CLIENT_SECRET
    )


def cipher():
    return Fernet(settings.GOOGLE_INTEGRATION_ENCRYPTION_KEY.encode())


def encrypt(value):
    return cipher().encrypt(value.encode()).decode()


def decrypt(value):
    try:
        return cipher().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        raise GoogleError(
            "Reconnect Google to restore access.", reconnect=True
        ) from None


def redirect_uri():
    return settings.FRONTEND_URL.rstrip("/") + "/profile/google/callback"


def begin(profile, service):
    if service not in SCOPES:
        raise ValidationError("Unknown Google service.")
    if not configured():
        raise ValidationError(
            "Google connections need configuration by the CRM administrator."
        )
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    GoogleConnection.objects.update_or_create(
        org=profile.org,
        profile=profile,
        service=service,
        defaults={
            "oauth_state_hash": hashlib.sha256(state.encode()).hexdigest(),
            "encrypted_verifier": encrypt(verifier),
            "oauth_started_at": timezone.now(),
        },
    )
    query = urlencode(
        {
            "client_id": settings.GOOGLE_INTEGRATION_CLIENT_ID,
            "redirect_uri": redirect_uri(),
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
            "scope": " ".join(IDENTITY_SCOPES + SCOPES[service]),
            "state": state,
            "code_challenge": base64.urlsafe_b64encode(
                hashlib.sha256(verifier.encode()).digest()
            )
            .rstrip(b"=")
            .decode(),
            "code_challenge_method": "S256",
        }
    )
    return {
        "url": "https://accounts.google.com/o/oauth2/v2/auth?" + query,
        "state": state,
    }


def token_request(payload):
    try:
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_INTEGRATION_CLIENT_ID,
                "client_secret": settings.GOOGLE_INTEGRATION_CLIENT_SECRET,
                **payload,
            },
            timeout=20,
        )
        if response.status_code == 400:
            raise GoogleError("Reconnect Google to restore access.", reconnect=True)
        if not response.ok:
            raise GoogleError()
        return response.json()
    except (requests.RequestException, ValueError):
        raise GoogleError() from None


def complete(profile, code, state):
    if not isinstance(state, str) or not state or not isinstance(code, str) or not code:
        raise ValidationError("The Google authorization is incomplete. Connect again.")
    with transaction.atomic():
        conn = (
            GoogleConnection.objects.select_for_update()
            .filter(
                org=profile.org,
                profile=profile,
                oauth_state_hash=hashlib.sha256(state.encode()).hexdigest(),
                oauth_started_at__gte=timezone.now() - timedelta(minutes=10),
            )
            .first()
        )
        if not conn:
            raise ValidationError("The Google authorization expired. Connect again.")
        verifier = decrypt(conn.encrypted_verifier)
        generation = conn.generation
        conn.oauth_state_hash = conn.encrypted_verifier = ""
        conn.save(update_fields=["oauth_state_hash", "encrypted_verifier"])
    tokens = token_request(
        {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri(),
        }
    )
    try:
        identity = verify_oauth2_token(
            tokens.get("id_token", ""),
            GoogleRequest(),
            settings.GOOGLE_INTEGRATION_CLIENT_ID,
        )
    except Exception:
        raise GoogleError(
            "Could not verify the Google account. Connect again.", reconnect=True
        ) from None
    if (
        not identity.get("email_verified")
        or not identity.get("email")
        or not identity.get("sub")
    ):
        raise GoogleError("Use a verified Google email address.", reconnect=True)
    scopes = tokens.get("scope", "").split()
    if not set(SCOPES[conn.service]).issubset(scopes):
        raise GoogleError(
            "The required Google permissions were not granted. Connect again.",
            reconnect=True,
        )
    refresh = tokens.get("refresh_token")
    if not refresh:
        raise GoogleError(
            "Google did not grant offline access. Connect again.", reconnect=True
        )
    with transaction.atomic():
        conn = (
            GoogleConnection.objects.select_for_update()
            .filter(pk=conn.pk, generation=generation)
            .first()
        )
        if not conn:
            raise GoogleError("Connection changed. Connect again.")
        conn.events.all().delete()
        conn.mirrors.all().delete()
        conn.mail_activity.all().delete()
        import uuid

        conn.generation = uuid.uuid4()
        conn.email = identity["email"].lower()
        conn.subject = identity["sub"]
        conn.encrypted_refresh_token = encrypt(refresh)
        conn.scopes = scopes
        conn.status = "connected"
        conn.error = ""
        conn.history_id = ""
        conn.initial_history_id = ""
        conn.mail_page_token = ""
        conn.last_sync = conn.sync_started_at = None
        conn.calendar_id, conn.calendar_name = "primary", "Primary calendar"
        conn.save()
    return conn


class GoogleAPI:
    def __init__(self, conn):
        result = token_request(
            {
                "grant_type": "refresh_token",
                "refresh_token": decrypt(conn.encrypted_refresh_token),
            }
        )
        self.token = result.get("access_token")
        if not self.token:
            raise GoogleError("Reconnect Google to restore access.", reconnect=True)

    def get(self, path, params=None):
        return self.request("GET", path, params=params)

    def request(self, method, path, params=None, body=None, etag=None):
        # Paths are assembled exclusively from our Google API routes.
        try:
            headers = {"Authorization": "Bearer " + self.token}
            if etag:
                headers["If-Match"] = etag
            response = requests.request(
                method,
                "https://www.googleapis.com/" + path,
                headers=headers,
                params=params,
                json=body,
                timeout=20,
            )
            if response.status_code in (401, 403):
                raise GoogleError(
                    "Google access was denied. Check permissions and reconnect.",
                    reconnect=True,
                    status=response.status_code,
                )
            if not response.ok:
                raise GoogleError(status=response.status_code)
            return response.json() if response.content else {}
        except (requests.RequestException, ValueError):
            raise GoogleError() from None


def connection_status(profile):
    rows = {
        row.service: row
        for row in GoogleConnection.objects.filter(org=profile.org, profile=profile)
    }
    result = {}
    enabled = configured()
    for service in SCOPES:
        row = rows.get(service)
        result["google_calendar" if service == "calendar" else service] = {
            "configured": enabled,
            "status": row.status
            if row
            else ("disconnected" if enabled else "setup_required"),
            "email": row.email if row else None,
            "last_sync": row.last_sync if row else None,
            "error": row.error if row else "",
            "syncing": bool(row and row.sync_started_at),
            "can_send": bool(
                row and row.status == "connected" and GMAIL_SEND_SCOPE in row.scopes
            ),
            "calendar": row.calendar_name if row and service == "calendar" else None,
        }
    return result
