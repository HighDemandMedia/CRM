"""Record email projections; every query remains private to the connected user."""

from urllib.parse import quote

from django.db.models import F, Q, Window
from django.db.models.functions import Lower, RowNumber, Trim
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound

from accounts.access import assert_account_access
from accounts.models import Account
from common.models import GoogleMailActivity
from common.permissions import is_org_admin
from common.rbac import configured, require, scoped
from contacts.access import assert_contact_access
from contacts.models import Contact


def visible_mail_contacts(profile):
    require(profile, "contacts", "view")
    contacts = scoped(Contact.objects.filter(is_active=True), profile)
    if not configured(profile) and not is_org_admin(profile):
        # Match the legacy detail permission, including assigned companies.
        contacts = contacts.filter(
            Q(created_by=profile.user)
            | Q(assigned_to=profile)
            | Q(account__assigned_to=profile)
            | Q(account_contacts__assigned_to=profile)
        ).distinct()
    return contacts


def record_contacts(profile, kind, pk):
    contacts = visible_mail_contacts(profile)
    if kind == "contact":
        contact = get_object_or_404(contacts, pk=pk)
        assert_contact_access(profile, contact)
        return contacts.filter(pk=contact.pk)
    if kind != "company":
        raise NotFound()
    require(profile, "companies", "view")
    account = get_object_or_404(scoped(Account.objects.all(), profile), pk=pk)
    assert_account_access(profile, account)
    # Both the primary company and explicitly linked companies are supported.
    return contacts.filter(Q(account=account) | Q(account_contacts=account)).distinct()


def mail_rows(profile, contacts):
    emails = contacts.annotate(mail_address=Lower(Trim("email"))).values("mail_address")
    return GoogleMailActivity.objects.filter(
        org=profile.org,
        connection__org=profile.org,
        connection__profile=profile,
        connection__service="gmail",
        contact_email__in=emails,
    ).defer("encrypted_body")


def unique_messages(rows):
    # A message to two linked contacts must appear just once on a company.
    return rows.annotate(
        message_position=Window(
            expression=RowNumber(),
            partition_by=[F("message_id")],
            order_by=F("id").asc(),
        )
    ).filter(message_position=1)


def mail_summary(row):
    return {
        "id": str(row.pk),
        "thread_id": row.thread_id,
        "subject": row.subject,
        "sender": row.sender,
        "recipients": row.recipients,
        "cc": row.cc,
        "direction": row.direction,
        "at": row.occurred_at,
        "account": row.connection.email,
        "href": "https://mail.google.com/mail/u/?authuser="
        + quote(row.connection.email, safe="")
        + "#all/"
        + quote(row.thread_id, safe=""),
    }


def record_mail_activity(profile, kind, pk):
    contacts = record_contacts(profile, kind, pk)
    rows = unique_messages(mail_rows(profile, contacts)).select_related("connection")
    return [mail_summary(row) for row in rows.order_by("-occurred_at", "-id")[:100]]
