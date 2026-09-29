import base64
from datetime import timedelta
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from cryptography.fernet import Fernet
from django.utils import timezone

from common.google_integration import (
    SCOPES,
    GoogleError,
    begin,
    complete,
    decrypt,
    encrypt,
)
from common.google_sync import (
    event_times,
    fingerprint,
    message_body,
    sync_calendar,
    sync_gmail,
    sync_mirrors,
)
from common.models import (
    GoogleCalendarEvent,
    GoogleCalendarMirror,
    GoogleConnection,
    GoogleMailActivity,
    SalesAppointment,
)
from contacts.models import Contact

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def google_settings(settings):
    settings.GOOGLE_INTEGRATION_CLIENT_ID = "test-client"
    settings.GOOGLE_INTEGRATION_CLIENT_SECRET = "test-secret"
    settings.GOOGLE_INTEGRATION_ENCRYPTION_KEY = Fernet.generate_key().decode()
    settings.FRONTEND_URL = "https://crm.example.com"


@pytest.fixture
def conn(admin_profile, org_a):
    return GoogleConnection.objects.create(
        org=org_a,
        profile=admin_profile,
        service="gmail",
        email="owner@example.com",
        status="connected",
        encrypted_refresh_token=encrypt("refresh-secret"),
    )


def test_oauth_pkce_and_single_use_bound_to_profile(admin_profile, user_profile):
    request = begin(admin_profile, "gmail")
    query = parse_qs(urlparse(request["url"]).query)
    assert query["code_challenge_method"] == ["S256"]
    assert query["redirect_uri"] == ["https://crm.example.com/profile/google/callback"]
    assert "gmail.readonly" in query["scope"][0]
    row = GoogleConnection.objects.get(profile=admin_profile)
    assert request["state"] not in row.oauth_state_hash
    with (
        pytest.raises(Exception),
        patch("common.google_integration.token_request") as exchange,
    ):
        complete(user_profile, "code", request["state"])
    exchange.assert_not_called()
    with (
        patch(
            "common.google_integration.token_request",
            return_value={
                "id_token": "id",
                "refresh_token": "secret",
                "scope": " ".join(SCOPES["gmail"]),
            },
        ),
        patch(
            "common.google_integration.verify_oauth2_token",
            return_value={
                "email": "owner@example.com",
                "email_verified": True,
                "sub": "123",
            },
        ),
    ):
        result = complete(admin_profile, "code", request["state"])
        assert decrypt(result.encrypted_refresh_token) == "secret"
        with pytest.raises(Exception):
            complete(admin_profile, "code", request["state"])


def test_oauth_rejects_missing_scope_and_expired_state(admin_profile):
    req = begin(admin_profile, "calendar")
    with (
        patch(
            "common.google_integration.token_request",
            return_value={"id_token": "id", "refresh_token": "secret", "scope": ""},
        ),
        patch(
            "common.google_integration.verify_oauth2_token",
            return_value={
                "email": "owner@example.com",
                "email_verified": True,
                "sub": "123",
            },
        ),
    ):
        with pytest.raises(GoogleError, match="permissions"):
            complete(admin_profile, "code", req["state"])
    req = begin(admin_profile, "calendar")
    GoogleConnection.objects.filter(profile=admin_profile).update(
        oauth_started_at=timezone.now() - timedelta(minutes=11)
    )
    with (
        pytest.raises(Exception),
        patch("common.google_integration.token_request") as exchange,
    ):
        complete(admin_profile, "code", req["state"])
    exchange.assert_not_called()


def test_disconnect_only_own_connection_and_cleans_mail(
    admin_client, user_client, conn, org_a
):
    GoogleMailActivity.objects.create(
        org=org_a,
        connection=conn,
        message_id="m",
        thread_id="t",
        contact_email="contact@example.com",
        sender="sender@example.com",
        direction="received",
        occurred_at=timezone.now(),
        encrypted_body=encrypt("private"),
    )
    assert (
        user_client.post(
            "/api/integrations/google/",
            {"service": "gmail", "operation": "disconnect"},
            format="json",
        ).status_code
        == 404
    )
    assert GoogleConnection.objects.filter(pk=conn.pk).exists()
    assert (
        admin_client.post(
            "/api/integrations/google/",
            {"service": "gmail", "operation": "disconnect"},
            format="json",
        ).status_code
        == 200
    )
    assert not GoogleMailActivity.objects.exists()


def test_mail_privacy_even_between_org_admin_and_member(
    admin_client, user_client, org_b_client, conn, org_a
):
    Contact.objects.create(
        org=org_a, first_name="Customer", email="contact@example.com"
    )
    row = GoogleMailActivity.objects.create(
        org=org_a,
        connection=conn,
        message_id="m",
        thread_id="t",
        contact_email="contact@example.com",
        sender="contact@example.com",
        direction="received",
        occurred_at=timezone.now(),
        encrypted_body=encrypt("<script>not executed</script>"),
    )
    path = f"/api/integrations/google/mail/{row.pk}/"
    assert admin_client.get(path).data["body"] == "<script>not executed</script>"
    assert user_client.get(path).status_code == 404
    assert org_b_client.get(path).status_code == 404
    Contact.objects.filter(email="contact@example.com").update(
        email="changed@example.com"
    )
    assert admin_client.get(path).status_code == 404


def test_sync_gmail_matches_contacts_deduplicates_and_encrypts(conn, org_a):
    Contact.objects.create(org=org_a, first_name="Customer", email="client@example.com")
    metadata = {
        "id": "m1",
        "threadId": "t1",
        "labelIds": ["SENT"],
        "internalDate": "1700000000000",
        "payload": {
            "headers": [
                {"name": "From", "value": "owner@example.com"},
                {"name": "To", "value": "Client <client@example.com>"},
                {"name": "Subject", "value": "Proposal"},
            ]
        },
    }
    body = {
        "payload": {
            "mimeType": "text/plain",
            "body": {"data": base64.urlsafe_b64encode(b"Full email message").decode()},
        }
    }

    def response(path, params=None):
        if path.endswith("/profile"):
            return {"historyId": "h1"}
        if path.endswith("/messages"):
            return {"messages": [{"id": "m1"}]}
        if path.endswith("/history"):
            return {
                "historyId": "h2",
                "history": [{"messagesAdded": [{"message": {"id": "m1"}}]}],
            }
        return body if params.get("format") == "full" else metadata

    api = Mock()
    api.get.side_effect = response
    sync_gmail(conn, api)
    row = GoogleMailActivity.objects.get()
    assert row.direction == "sent" and row.subject == "Proposal"
    assert "Full email" not in row.encrypted_body
    assert decrypt(row.encrypted_body) == "Full email message"
    conn.refresh_from_db()
    sync_gmail(conn, api)
    assert GoogleMailActivity.objects.count() == 1


def test_mail_excludes_unmatched_contacts_and_drafts(conn):
    api = Mock()
    api.get.side_effect = [
        {"historyId": "h"},
        {"messages": [{"id": "m"}]},
        {"id": "m", "labelIds": ["DRAFT"], "payload": {}},
    ]
    sync_gmail(conn, api)
    assert not GoogleMailActivity.objects.exists()
    assert api.get.call_count == 3


def test_mail_initial_pagination_resumes_without_skipping_history(conn):
    api = Mock()
    api.get.side_effect = [
        {"historyId": "h0"},
        {"messages": [], "nextPageToken": "next"},
    ]
    sync_gmail(conn, api)
    conn.refresh_from_db()
    assert (
        conn.history_id == ""
        and conn.mail_page_token == "next"
        and conn.initial_history_id == "h0"
    )
    api.get.side_effect = [{"historyId": "h1"}, {"messages": []}]
    sync_gmail(conn, api)
    conn.refresh_from_db()
    assert conn.history_id == "h0" and not conn.mail_page_token
    assert api.get.call_args.args[1]["pageToken"] == "next"


def test_html_mail_becomes_text_without_remote_content():
    raw = b'<p>Hello</p><img src="https://tracker.test/pixel"><script>steal()</script><p>World</p>'
    text = message_body(
        Mock(),
        "m",
        {
            "mimeType": "text/html",
            "body": {"data": base64.urlsafe_b64encode(raw).decode()},
        },
    )
    assert (
        "Hello" in text
        and "World" in text
        and "steal" not in text
        and "tracker" not in text
    )


def appointment(conn):
    return SalesAppointment.objects.create(
        org=conn.org,
        host=conn.profile,
        created_by=conn.profile.user,
        title="Meeting",
        internal_notes="Meeting notes",
        starts_at=timezone.now() + timedelta(days=1),
        ends_at=timezone.now() + timedelta(days=1, hours=1),
    )


def test_calendar_export_includes_notes_and_no_invites(conn):
    conn.service = "calendar"
    conn.save()
    appt = appointment(conn)
    api = Mock()
    api.get.side_effect = GoogleError(status=404)
    api.request.return_value = {"etag": "v1"}
    sync_mirrors(conn, api, "calendar/v3/calendars/primary", True)
    body = api.request.call_args.kwargs["body"]
    assert body["description"] == "Meeting notes" and body["summary"] == "Meeting"
    assert "attendees" not in body
    assert api.request.call_args.kwargs["params"] == {"sendUpdates": "none"}
    assert GoogleCalendarMirror.objects.get().appointment == appt


def test_google_changes_update_crm_notes_and_time(conn):
    conn.service = "calendar"
    conn.save()
    appt = appointment(conn)
    GoogleCalendarMirror.objects.create(
        org=conn.org,
        connection=conn,
        appointment=appt,
        external_id="g1",
        etag="v1",
        fingerprint=fingerprint(appt),
    )
    new_start = appt.starts_at + timedelta(hours=2)
    new_end = appt.ends_at + timedelta(hours=2)
    api = Mock()
    api.get.return_value = {
        "etag": "v2",
        "summary": "Changed in Google",
        "description": "<p>New notes</p>",
        "start": {"dateTime": new_start.isoformat()},
        "end": {"dateTime": new_end.isoformat()},
    }
    sync_mirrors(conn, api, "calendar/v3/calendars/primary", True)
    appt.refresh_from_db()
    assert (
        appt.title == "Changed in Google"
        and appt.internal_notes == "New notes"
        and appt.starts_at == new_start
    )
    api.request.assert_not_called()


def test_calendar_conflict_does_not_overwrite(conn):
    conn.service = "calendar"
    conn.save()
    appt = appointment(conn)
    GoogleCalendarMirror.objects.create(
        org=conn.org,
        connection=conn,
        appointment=appt,
        external_id="g1",
        etag="v1",
        fingerprint=fingerprint(appt),
    )
    appt.title = "Changed locally"
    appt.save()
    api = Mock()
    api.get.return_value = {
        "etag": "v2",
        "summary": "Changed remotely",
        "start": {"dateTime": appt.starts_at.isoformat()},
        "end": {"dateTime": appt.ends_at.isoformat()},
    }
    with pytest.raises(GoogleError, match="conflict"):
        sync_mirrors(conn, api, "calendar/v3/calendars/primary", True)
    appt.refresh_from_db()
    assert appt.title == "Changed locally"
    api.request.assert_not_called()


def test_calendar_cache_is_private_and_hides_mirrors(
    admin_client, user_client, org_b_client, conn
):
    conn.service = "calendar"
    conn.save()
    appt = appointment(conn)
    GoogleCalendarEvent.objects.create(
        org=conn.org,
        connection=conn,
        external_id="external",
        title="Personal meeting",
        starts_at=appt.starts_at,
        ends_at=appt.ends_at,
    )
    GoogleCalendarMirror.objects.create(
        org=conn.org, connection=conn, appointment=appt, external_id="mirror"
    )
    GoogleCalendarEvent.objects.create(
        org=conn.org,
        connection=conn,
        external_id="mirror",
        title="Already in CRM",
        starts_at=appt.starts_at,
        ends_at=appt.ends_at,
    )
    path = "/api/integrations/google/events/"
    params = {
        "start": timezone.now().isoformat(),
        "end": (timezone.now() + timedelta(days=7)).isoformat(),
    }
    assert [x["title"] for x in admin_client.get(path, params).data["events"]] == [
        "Personal meeting"
    ]
    assert user_client.get(path, params).data["events"] == []
    assert org_b_client.get(path, params).data["events"] == []


def test_all_day_dates_keep_exclusive_end():
    start, end, all_day = event_times(
        {"start": {"date": "2026-09-29"}, "end": {"date": "2026-10-01"}},
        "America/New_York",
    )
    assert all_day and (end - start).days == 2 and start.hour == 0


def test_calendar_failed_page_does_not_clear_cache(conn):
    conn.service = "calendar"
    conn.save()
    appt = appointment(conn)
    GoogleCalendarEvent.objects.create(
        org=conn.org,
        connection=conn,
        external_id="keep",
        title="Keep",
        starts_at=appt.starts_at,
        ends_at=appt.ends_at,
    )
    api = Mock()
    api.get.side_effect = [
        {"accessRole": "reader", "timeZone": "UTC"},
        {"items": [], "nextPageToken": "next"},
        GoogleError(),
    ]
    with pytest.raises(GoogleError):
        sync_calendar(conn, api)
    assert conn.events.count() == 1


def test_status_does_not_expose_tokens_or_mail(admin_client, conn):
    response = admin_client.get("/api/integrations/google/")
    assert response.status_code == 200
    assert "refresh-secret" not in str(response.data)
    assert "encrypted_refresh_token" not in str(response.data)
    assert response.data["gmail"]["email"] == conn.email


def test_google_busy_blocks_new_crm_booking(conn, admin_profile):
    from types import SimpleNamespace

    from django.db import transaction

    from common.views.sales_appointment_views import lock_host_and_check

    conn.service = "calendar"
    conn.save()
    appt = appointment(conn)
    start, end = appt.starts_at + timedelta(hours=3), appt.ends_at + timedelta(hours=3)
    GoogleCalendarEvent.objects.create(
        org=conn.org,
        connection=conn,
        external_id="busy",
        title="Personal",
        starts_at=start,
        ends_at=end,
    )
    with transaction.atomic(), pytest.raises(Exception, match="already booked"):
        lock_host_and_check(
            SimpleNamespace(profile=admin_profile), admin_profile.pk, start, end
        )


def test_crm_details_can_edit_meeting_notes(admin_client, conn):
    appt = appointment(conn)
    response = admin_client.patch(
        f"/api/sales-appointments/{appt.pk}/",
        {"operation": "details", "title": "Review", "internal_notes": "Updated notes"},
        format="json",
    )
    assert response.status_code == 200, response.data
    appt.refresh_from_db()
    assert appt.title == "Review" and appt.internal_notes == "Updated notes"


def test_reconnect_recovers_remote_event_without_duplicate(conn):
    conn.service = "calendar"
    conn.save()
    appt = appointment(conn)
    api = Mock()
    api.get.return_value = {
        "etag": "existing",
        "summary": "Existing meeting",
        "description": "Existing notes",
        "start": {"dateTime": appt.starts_at.isoformat()},
        "end": {"dateTime": appt.ends_at.isoformat()},
    }
    sync_mirrors(conn, api, "calendar/v3/calendars/primary", True)
    api.request.assert_not_called()
    appt.refresh_from_db()
    assert appt.title == "Existing meeting"
    assert conn.mirrors.count() == 1


def test_google_cancel_is_idempotent(conn):
    conn.service = "calendar"
    conn.save()
    appt = appointment(conn)
    GoogleCalendarMirror.objects.create(
        org=conn.org,
        connection=conn,
        appointment=appt,
        external_id="g",
        etag="before",
        fingerprint=fingerprint(appt),
    )
    api = Mock()
    api.get.side_effect = GoogleError(status=404)
    sync_mirrors(conn, api, "calendar/v3/calendars/primary", True)
    appt.refresh_from_db()
    assert appt.cancelled_at
    changes = len(appt.change_history)
    sync_mirrors(conn, api, "calendar/v3/calendars/primary", True)
    appt.refresh_from_db()
    assert len(appt.change_history) == changes


def test_sync_error_requires_reconnect_without_leaking_secret(conn):
    from common.tasks import sync_google_connection

    with patch(
        "common.google_integration.token_request",
        side_effect=GoogleError("Reconnect Google to restore access.", reconnect=True),
    ):
        sync_google_connection(str(conn.org_id), str(conn.pk))
    conn.refresh_from_db()
    assert conn.status == "reconnect" and conn.sync_started_at is None
    assert "refresh-secret" not in conn.error


def test_calendar_notes_escape_markup_on_export(conn):
    conn.service = "calendar"
    conn.save()
    appt = appointment(conn)
    appt.internal_notes = "Budget < 100 & literal <tag>"
    appt.save()
    api = Mock()
    api.get.side_effect = GoogleError(status=404)
    api.request.return_value = {"etag": "v1"}
    sync_mirrors(conn, api, "calendar/v3/calendars/primary", True)
    assert (
        api.request.call_args.kwargs["body"]["description"]
        == "Budget &lt; 100 &amp; literal &lt;tag&gt;"
    )
