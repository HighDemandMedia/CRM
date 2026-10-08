from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from django.utils import timezone

from accounts.models import Account
from common.google_integration import decrypt, encrypt
from common.google_mail import record_mail_activity
from common.google_sync import sync_gmail
from common.models import GoogleConnection, GoogleMailActivity
from common.tests.test_google_integrations import google_settings  # noqa: F401
from contacts.models import Contact

pytestmark = pytest.mark.django_db


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


def message(
    conn, contact, *, message_id="m1", thread="t1", direction="received", at=None
):
    return GoogleMailActivity.objects.create(
        org=conn.org,
        connection=conn,
        contact_email=contact.email.lower(),
        message_id=message_id,
        thread_id=thread,
        subject="Proposal",
        direction=direction,
        sender=contact.email if direction == "received" else conn.email,
        recipients=[conn.email] if direction == "received" else [contact.email],
        encrypted_body=encrypt("Private message"),
        occurred_at=at or timezone.now(),
    )


def endpoint(record, kind="contact"):
    return f"/api/integrations/google/records/{kind}/{record.pk}/mail/"


def test_threads_count_messages_and_lazy_load_chronologically(
    admin_client, conn, org_a
):
    contact = Contact.objects.create(
        org=org_a, first_name="Client", email="client@example.com"
    )
    first = message(conn, contact, at=timezone.now() - timedelta(days=1))
    second = message(conn, contact, message_id="m2", direction="sent")
    result = admin_client.get(endpoint(contact))
    assert result.status_code == 200, result.data
    thread = result.data["results"][0]
    assert thread["message_count"] == 2 and thread["id"] == str(second.pk)
    assert "body" not in thread and "encrypted_body" not in thread
    assert result["Cache-Control"] == "private, no-store"
    detail = admin_client.get(endpoint(contact), {"thread": "t1"})
    assert [row["id"] for row in detail.data["results"]] == [
        str(first.pk),
        str(second.pk),
    ]
    assert (
        admin_client.get(endpoint(contact), {"direction": "received"}).data["results"][
            0
        ]["message_count"]
        == 2
    )
    assert not admin_client.get(endpoint(contact), {"q": "no match"}).data["results"]


def test_company_rollup_is_unique_and_scoped_to_linked_contacts(
    admin_client, conn, org_a
):
    company = Account.objects.create(org=org_a, name="Client company")
    a = Contact.objects.create(org=org_a, email="a@example.com", account=company)
    b = Contact.objects.create(org=org_a, email="b@example.com")
    outside = Contact.objects.create(org=org_a, email="outside@example.com")
    company.contacts.add(a, b)
    for contact in [a, b]:
        row = message(conn, contact, direction="sent")
        row.recipients = [a.email, b.email]
        row.save()
    message(conn, outside, message_id="other", thread="unrelated")
    result = admin_client.get(endpoint(company, "company"))
    assert result.status_code == 200, result.data
    assert len(result.data["results"]) == 1
    assert result.data["results"][0]["message_count"] == 1
    assert len(result.data["results"][0]["contacts"]) == 2
    detail = admin_client.get(endpoint(company, "company"), {"thread": "t1"})
    assert len(detail.data["results"]) == 1
    assert len(record_mail_activity(conn.profile, "company", company.pk)) == 1
    assert not admin_client.get(
        endpoint(company, "company"), {"contact": str(outside.pk)}
    ).data["results"]


def test_record_mail_remains_private_between_users_and_tenants(
    admin_client, user_client, org_b_client, conn, org_a
):
    contact = Contact.objects.create(org=org_a, email="client@example.com")
    message(conn, contact)
    response = user_client.get(endpoint(contact))
    assert response.status_code in (403, 404) or response.data["results"] == []
    assert org_b_client.get(endpoint(contact)).status_code in (403, 404)
    assert admin_client.get(endpoint(contact)).data["results"]


def test_pagination_exposes_older_threads_and_messages(admin_client, conn, org_a):
    contact = Contact.objects.create(org=org_a, email="client@example.com")
    for index in range(23):
        message(conn, contact, message_id=f"m{index}", thread=f"t{index:02}")
    first = admin_client.get(endpoint(contact)).data
    second = admin_client.get(endpoint(contact), {"offset": first["next_offset"]}).data
    assert len(first["results"]) == 20 and len(second["results"]) == 3
    assert not (
        {x["thread_id"] for x in first["results"]}
        & {x["thread_id"] for x in second["results"]}
    )
    assert second["next_offset"] is None
    GoogleMailActivity.objects.filter(connection=conn).update(thread_id="all")
    page = admin_client.get(endpoint(contact), {"thread": "all"}).data
    assert len(page["results"]) == 20 and page["next_offset"] == 20


@pytest.mark.parametrize(
    "params",
    [{"offset": "-1"}, {"offset": "bad"}, {"direction": "bad"}, {"contact": "invalid"}],
)
def test_invalid_filters_are_rejected(admin_client, conn, org_a, params):
    contact = Contact.objects.create(org=org_a, email="client@example.com")
    assert admin_client.get(endpoint(contact), params).status_code == 400


def test_sync_now_queues_only_the_current_users_connection(admin_client, conn, org_a):
    contact = Contact.objects.create(org=org_a, email="client@example.com")
    with patch("common.tasks.sync_google_connection.delay") as queue:
        result = admin_client.post(endpoint(contact))
    assert result.status_code == 200
    queue.assert_called_once_with(str(org_a.pk), str(conn.pk))


def test_new_contact_restarts_bounded_history_import_without_clearing_cache(
    conn, org_a
):
    a = Contact.objects.create(org=org_a, email="existing@example.com")
    cached = message(conn, a)
    api = Mock()
    api.get.side_effect = [{"historyId": "h1"}, {"messages": []}]
    sync_gmail(conn, api)
    conn.refresh_from_db()
    old_fingerprint = conn.mail_contacts_fingerprint
    Contact.objects.create(org=org_a, email="new@example.com")
    api.reset_mock()
    api.get.side_effect = [
        {"historyId": "h2"},
        {"messages": [], "nextPageToken": "page2"},
    ]
    sync_gmail(conn, api)
    conn.refresh_from_db()
    assert conn.mail_contacts_fingerprint != old_fingerprint
    assert conn.mail_page_token == "page2" and conn.history_id == ""
    assert GoogleMailActivity.objects.filter(pk=cached.pk).exists()
    assert api.get.call_args.args[0].endswith("/messages")
    assert api.get.call_args.args[1]["maxResults"] == 50


def test_cc_is_separate_and_still_matches_contacts(conn, org_a):
    import base64

    contact = Contact.objects.create(org=org_a, email="cc@example.com")
    api = Mock()
    api.get.side_effect = [
        {"historyId": "h1"},
        {"messages": [{"id": "m1"}]},
        {
            "threadId": "t1",
            "internalDate": "1700000000000",
            "labelIds": ["SENT"],
            "payload": {
                "headers": [
                    {"name": "From", "value": conn.email},
                    {"name": "To", "value": "to@example.com"},
                    {"name": "Cc", "value": contact.email},
                ]
            },
        },
        {
            "payload": {
                "mimeType": "text/plain",
                "body": {"data": base64.urlsafe_b64encode(b"Hello").decode()},
            }
        },
    ]
    sync_gmail(conn, api)
    mail = GoogleMailActivity.objects.get()
    assert mail.recipients == ["to@example.com"] and mail.cc == [contact.email]
    assert decrypt(mail.encrypted_body) == "Hello"


def test_admin_cannot_read_another_profiles_mail(
    admin_client, user_profile, org_a, conn
):
    contact = Contact.objects.create(org=org_a, email="client@example.com")
    other = GoogleConnection.objects.create(
        org=org_a, profile=user_profile, service="gmail", email="other@example.com"
    )
    message(other, contact)
    assert admin_client.get(endpoint(contact)).data["results"] == []


def test_legacy_company_rollup_excludes_inaccessible_contact(
    user_client, user_profile, org_a
):
    user_profile.access_role = None
    user_profile.save()
    company = Account.objects.create(
        org=org_a, name="Visible", created_by=user_profile.user
    )
    visible = Contact.objects.create(
        org=org_a, email="visible@example.com", created_by=user_profile.user
    )
    hidden = Contact.objects.create(org=org_a, email="hidden@example.com")
    company.contacts.add(visible, hidden)
    own = GoogleConnection.objects.create(
        org=org_a, profile=user_profile, service="gmail", email="own@example.com"
    )
    message(own, visible, message_id="visible", thread="visible")
    hidden_mail = message(own, hidden, message_id="hidden", thread="hidden")
    assert (
        user_client.get(f"/api/integrations/google/mail/{hidden_mail.pk}/").status_code
        == 404
    )
    response = user_client.get(endpoint(company, "company"))
    assert response.status_code == 200, response.data
    assert [row["thread_id"] for row in response.data["results"]] == ["visible"]
