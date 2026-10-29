"""Google OAuth and API calls. Credentials never leave the backend."""

import base64
import hashlib
import secrets
import uuid
from datetime import timedelta
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.id_token import verify_oauth2_token
from rest_framework.exceptions import ValidationError

from common.google_oauth_config import (
    authorization_client,
    client_config,
    grant_project,
    independent_disconnect,
    stored_client,
)
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
        revoked=False,
    ):
        super().__init__(message)
        self.reconnect = reconnect
        self.status = status
        self.revoked = revoked


def configured(service=None):
    try:
        cipher()
    except (ValueError, TypeError):
        return False
    if service:
        return authorization_client(service) is not None
    # Existing shared grants must keep syncing during a partial migration.
    return any(client_config(key).configured for key in ("legacy", "gmail", "calendar"))


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
    if not configured(service):
        raise ValidationError(
            "Google connections need configuration by the CRM administrator."
        )
    client = authorization_client(service)
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
            "pending_client_id": client.client_id,
            "pending_project_id": client.project_id,
        },
    )
    query = urlencode(
        {
            "client_id": client.client_id,
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


def token_request(payload, client):
    try:
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client.client_id,
                "client_secret": client.secret,
                **payload,
            },
            timeout=20,
        )
        if response.status_code == 400:
            if response.json().get("error") == "invalid_grant":
                raise GoogleError(
                    "Reconnect Google to restore access.", reconnect=True, revoked=True
                )
            raise GoogleError()
        if not response.ok:
            raise GoogleError()
        return response.json()
    except (requests.RequestException, ValueError):
        raise GoogleError() from None


def clear_unusable_connection(conn):
    """Forget private cache on a rejected refresh grant, not on transient failures."""
    with transaction.atomic():
        row = (
            GoogleConnection.objects.select_for_update()
            .filter(pk=conn.pk, generation=conn.generation)
            .first()
        )
        if not row:
            return
        row.events.all().delete()
        row.mail_activity.all().delete()
        row.mirrors.all().delete()
        row.encrypted_refresh_token = row.encrypted_verifier = row.oauth_state_hash = ""
        row.pending_client_id = row.pending_project_id = ""
        row.history_id = row.initial_history_id = row.mail_page_token = ""
        row.oauth_started_at = row.last_sync = row.sync_started_at = None
        row.scopes = []
        from common.google_calendar_push import reset_calendar_state

        reset_calendar_state(row)
        row.status = "reconnect"
        row.error = "Reconnect Google to restore access."
        row.generation = uuid.uuid4()
        row.save()


def revoke_google_account(conn):
    """Explicit project-wide Google revocation; local cleanup stays tenant-scoped.

    Google can revoke other grants for this Google account. Never invoke this
    implicitly when disconnecting just Gmail or Calendar.
    """
    identity = Q(subject=conn.subject) if conn.subject else Q(email__iexact=conn.email)
    connections = [
        row
        for row in GoogleConnection.objects.filter(
            identity, org=conn.org, profile=conn.profile
        )
        if grant_project(row) == grant_project(conn)
    ]
    revoke_connections(connections)


def revoke_connections(connections, *, allow_unusable=False):
    """Only called for an explicitly confirmed project or an isolated service."""
    sources = [row for row in connections if row.encrypted_refresh_token]
    if not sources and not allow_unusable:
        raise GoogleError("Remove access in your Google Account, then disconnect here.")
    revoked = False
    try:
        for source in sources:
            response = requests.post(
                "https://oauth2.googleapis.com/revoke",
                data={"token": decrypt(source.encrypted_refresh_token)},
                timeout=20,
            )
            if response.status_code == 200:
                revoked = True
                break
            # An expired Gmail token does not prove Calendar's token is revoked.
            if (
                response.status_code != 400
                or response.json().get("error") != "invalid_token"
            ):
                raise GoogleError(
                    "Could not revoke Google access. Try again or remove access in your Google Account."
                )
    except (requests.RequestException, ValueError):
        raise GoogleError(
            "Could not revoke Google access. Try again or remove access in your Google Account."
        ) from None
    with transaction.atomic():
        for row in connections:
            # Do not erase a connection replaced while Google was responding.
            GoogleConnection.objects.select_for_update().filter(
                pk=row.pk, generation=row.generation
            ).delete()

    return revoked


def disconnect(conn):
    if independent_disconnect(conn):
        # An already revoked/expired token cannot be revoked again. Allow local
        # cleanup without claiming that Google confirmed removal of its grant.
        return revoke_connections([conn], allow_unusable=True)
    if (
        conn.oauth_client_id
        and conn.oauth_client_id != client_config("legacy").client_id
    ):
        # A removed/misconfigured dedicated client must not silently turn revocation
        # into local-only deletion. Preserve the token so the operation can be retried.
        raise GoogleError(
            "Google connections need configuration by the CRM administrator."
        )
    # Never revoke an old shared grant implicitly, even after new clients are configured.
    with transaction.atomic():
        GoogleConnection.objects.select_for_update().filter(
            pk=conn.pk, generation=conn.generation
        ).delete()
    return False


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
        client = stored_client(conn.pending_client_id)
        project_id = conn.pending_project_id
        if client is None or (project_id and project_id != client.project_id):
            raise GoogleError(
                "Google connections need configuration by the CRM administrator."
            )
        generation = conn.generation
        conn.oauth_state_hash = conn.encrypted_verifier = ""
        conn.pending_client_id = conn.pending_project_id = ""
        conn.save(
            update_fields=[
                "oauth_state_hash",
                "encrypted_verifier",
                "pending_client_id",
                "pending_project_id",
            ]
        )
    tokens = token_request(
        {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri(),
        },
        client,
    )
    try:
        identity = verify_oauth2_token(
            tokens.get("id_token", ""),
            GoogleRequest(),
            client.client_id,
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
            .filter(
                pk=conn.pk,
                generation=generation,
                oauth_state_hash="",
                pending_client_id="",
            )
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
        conn.oauth_client_id = client.client_id
        conn.oauth_project_id = project_id
        conn.scopes = scopes
        conn.status = "connected"
        conn.error = ""
        conn.history_id = ""
        conn.initial_history_id = ""
        conn.mail_page_token = ""
        conn.last_sync = conn.sync_started_at = None
        conn.mail_sync_requested_at = conn.mail_watch_expires_at = (
            conn.mail_watch_renewed_at
        ) = None
        conn.mail_watch_topic = ""
        from common.google_calendar_push import reset_calendar_state

        reset_calendar_state(conn)
        conn.calendar_id, conn.calendar_name = "primary", "Primary calendar"
        conn.save()
    return conn


class GoogleAPI:
    def __init__(self, conn):
        client = stored_client(conn.oauth_client_id)
        if client is None:
            raise GoogleError(
                "Google connections need configuration by the CRM administrator."
            )
        try:
            result = token_request(
                {
                    "grant_type": "refresh_token",
                    "refresh_token": decrypt(conn.encrypted_refresh_token),
                },
                client,
            )
        except GoogleError as exc:
            if exc.revoked:
                clear_unusable_connection(conn)
            raise
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
    for service in SCOPES:
        row = rows.get(service)
        enabled = configured(service)
        target = authorization_client(service)
        result["google_calendar" if service == "calendar" else service] = {
            "configured": enabled,
            "status": row.status
            if row
            else ("disconnected" if enabled else "setup_required"),
            "email": row.email if row else None,
            "last_sync": row.last_sync if row else None,
            "error": row.error if row else "",
            "syncing": bool(row and row.sync_started_at),
            "independent_disconnect": bool(row and independent_disconnect(row)),
            "migration_available": bool(
                row
                and row.encrypted_refresh_token
                and target
                and target.client_id
                != (row.oauth_client_id or client_config("legacy").client_id)
            ),
            "can_send": bool(
                row and row.status == "connected" and GMAIL_SEND_SCOPE in row.scopes
            ),
            "calendar": row.calendar_name if row and service == "calendar" else None,
        }
    return result
