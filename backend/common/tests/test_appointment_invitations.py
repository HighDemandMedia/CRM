from datetime import timedelta
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from django.core import signing
from django.utils import timezone
from rest_framework.test import APIClient

from common.appointment_emails import _message, _recipient, queue_appointment_emails
from common.appointment_invitations import TOKEN_SALT, calendar_attachment, rsvp_link
from common.google_integration import GoogleError
from common.google_sync import sync_mirrors
from common.models import AppointmentEmailDelivery, GoogleConnection, SalesAppointment
from common.views.appointment_response_views import AppointmentResponseThrottle
from contacts.models import Contact

pytestmark = pytest.mark.django_db
PATH = "/api/appointment-response/"


@pytest.fixture
def meeting(admin_profile, org_a, settings):
    settings.FRONTEND_URL = "https://crm.example.com"
    settings.DEFAULT_FROM_EMAIL = "HDM <info@example.com>"
    start = timezone.now() + timedelta(days=2)
    row = SalesAppointment.objects.create(
        org=org_a,
        host=admin_profile,
        created_by=admin_profile.user,
        title="Planning",
        internal_notes="PRIVATE INTERNAL",
        starts_at=start,
        ends_at=start + timedelta(hours=1),
        invitation_provider="email",
    )
    row.contacts.add(
        Contact.objects.create(org=org_a, first_name="Guest", email="guest@example.com")
    )
    return row


def delivery(meeting):
    queue_appointment_emails(meeting, "scheduled")
    return AppointmentEmailDelivery.objects.get(
        appointment=meeting, email="guest@example.com"
    )


def token_for(meeting):
    return parse_qs(urlparse(rsvp_link(delivery(meeting))).query)["token"][0]


def test_read_limits_separate_valid_invitations_behind_web(meeting):
    from rest_framework.request import Request
    from rest_framework.test import APIRequestFactory

    token = token_for(meeting)
    payload = signing.loads(token, salt=TOKEN_SALT)
    payload[2] = "other@example.com"
    other = signing.dumps(payload, salt=TOKEN_SALT)
    factory, throttle = APIRequestFactory(), AppointmentResponseThrottle()

    def key(value):
        return throttle.get_cache_key(
            Request(factory.get(PATH, {"token": value})), None
        )

    assert key(token) != key(other)
    assert key("invalid-one") == key("invalid-two")


def test_email_has_actions_and_safe_calendar_attachment(meeting):
    row = delivery(meeting)
    message = _message(row, _recipient(row))
    html = message.alternatives[0].content
    assert all(
        "&amp;response=" + choice in html
        for choice in ["accepted", "tentative", "declined"]
    )
    assert "PRIVATE INTERNAL" not in message.message().as_string()
    assert message.attachments[0].get_content_type() == "text/calendar"
    assert message.attachments[0].get_param("method") == "REQUEST"
    data, _ = calendar_attachment(row)
    assert "UID:" + str(meeting.pk) in data and "SEQUENCE:0" in data
    assert all(len(line.encode()) <= 75 for line in data.split("\r\n"))
    row.action, row.revision = "cancelled", 1
    cancellation, method = calendar_attachment(row)
    assert method == "CANCEL" and "SEQUENCE:1" in cancellation
    assert "UID:" + str(meeting.pk) in cancellation
    assert "STATUS:CANCELLED" in cancellation and "URL:" not in cancellation


@pytest.mark.parametrize("status", ["accepted", "tentative", "declined"])
def test_rsvp_requires_post_and_only_changes_this_guest(meeting, status):
    token = token_for(meeting)
    client = APIClient()
    result = client.get(PATH, {"token": token, "response": status})
    assert result.status_code == 200
    assert "PRIVATE INTERNAL" not in str(result.data)
    meeting.refresh_from_db()
    assert meeting.guest_responses == {}
    result = client.post(PATH, {"token": token, "response": status}, format="json")
    assert result.status_code == 200, result.data
    meeting.refresh_from_db()
    assert meeting.guest_responses == {"guest@example.com": status}
    assert meeting.internal_notes == "PRIVATE INTERNAL"


@pytest.mark.parametrize(
    "invalid",
    ["tampered", "rescheduled", "cancelled", "removed", "closed", "other_org"],
)
def test_invalid_rsvp_cannot_mutate(meeting, invalid, org_b):
    token = token_for(meeting)
    if invalid == "tampered":
        token += "x"
    elif invalid == "rescheduled":
        meeting.starts_at += timedelta(hours=1)
        meeting.ends_at += timedelta(hours=1)
        meeting.save()
    elif invalid == "cancelled":
        meeting.cancelled_at = timezone.now()
        meeting.save()
    elif invalid == "removed":
        meeting.contacts.clear()
    elif invalid == "closed":
        meeting.org.closing_at = timezone.now()
        meeting.org.save()
    else:
        payload = signing.loads(token, salt=TOKEN_SALT)
        payload[0] = str(org_b.pk)
        token = signing.dumps(payload, salt=TOKEN_SALT)
    result = APIClient().post(
        PATH, {"token": token, "response": "accepted"}, format="json"
    )
    assert result.status_code == 410, result.data
    meeting.refresh_from_db()
    assert meeting.guest_responses == {}


def test_google_invitation_rsvp_and_reschedule_use_same_event(meeting):
    meeting.invitation_provider = "google"
    meeting.save()
    conn = GoogleConnection.objects.create(
        org=meeting.org,
        profile=meeting.host,
        service="calendar",
        status="connected",
        calendar_writable=True,
    )
    api = Mock()
    api.get.side_effect = GoogleError(status=404)
    api.request.return_value = {"etag": "v1"}
    sync_mirrors(conn, api, "calendar/v3/calendars/primary", True)
    body = api.request.call_args.kwargs["body"]
    assert body["description"] == "" and body["attendees"] == [
        {
            "email": "guest@example.com",
            "displayName": "Guest",
            "responseStatus": "needsAction",
        }
    ]
    assert api.request.call_args.kwargs["params"] == {"sendUpdates": "all"}
    event_id = body["id"]
    api.get.side_effect = None
    api.get.return_value = {
        **body,
        "etag": "v2",
        "attendees": [
            {"email": "guest@example.com", "responseStatus": "accepted"},
            {"email": "uninvited@example.com", "responseStatus": "accepted"},
        ],
    }
    api.request.reset_mock()
    with patch("common.views.sales_appointment_views.sync_attendee") as activity:
        sync_mirrors(conn, api, "calendar/v3/calendars/primary", True)
    api.request.assert_not_called()
    activity.assert_not_called()
    meeting.refresh_from_db()
    assert meeting.guest_responses == {"guest@example.com": "accepted"}
    meeting.starts_at += timedelta(hours=1)
    meeting.ends_at += timedelta(hours=1)
    meeting.save()
    # An RSVP may race with an edit without creating a false meeting conflict.
    api.get.return_value["etag"] = "v3"
    api.request.return_value = {"etag": "v4"}
    sync_mirrors(conn, api, "calendar/v3/calendars/primary", True)
    assert api.request.call_args.args == (
        "PATCH",
        "calendar/v3/calendars/primary/events/" + event_id,
    )
    assert api.request.call_args.kwargs["params"] == {"sendUpdates": "all"}
    updated = api.request.call_args.kwargs["body"]
    assert updated["attendees"][0]["responseStatus"] == "accepted"
    api.get.return_value = {**updated, "etag": "v4"}
    meeting.cancelled_at = timezone.now()
    meeting.save()
    sync_mirrors(conn, api, "calendar/v3/calendars/primary", True)
    assert api.request.call_args.args[0] == "DELETE"
    assert api.request.call_args.args[1].endswith("/" + event_id)
    assert api.request.call_args.kwargs["params"] == {"sendUpdates": "all"}
    assert conn.mirrors.count() == 1
    queue_appointment_emails(meeting, "cancelled")
    assert list(
        AppointmentEmailDelivery.objects.values_list("profile_id", flat=True)
    ) == [meeting.host_id]


def test_company_email_invitation(meeting):
    from accounts.models import Account

    company = Account.objects.create(
        org=meeting.org, name="Company", email="company@example.com"
    )
    meeting.companies.add(company)
    queue_appointment_emails(meeting, "scheduled")
    row = AppointmentEmailDelivery.objects.get(appointment=meeting, company=company)
    assert _recipient(row)[0] == "Company"
    assert _message(row, _recipient(row)).attachments
    company.is_active = False
    company.save()
    row.refresh_from_db()
    assert _recipient(row) is None
