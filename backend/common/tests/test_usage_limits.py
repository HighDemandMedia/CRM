from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from crum import impersonate
from django.apps import apps
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from common.audit_log import SecurityAuditLog
from common.models import Org, OrganizationInvitation, Profile, User
from common.platform_usage import organization_usage
from common.testing import _make_authenticated_client, rls_org
from common.usage_limits import (
    RECORD_RESOURCES,
    OrganizationLimitReached,
    resource_count,
)
from contacts.models import Contact

pytestmark = pytest.mark.django_db


def limit(org, **values):
    Org.objects.filter(pk=org.pk).update(usage_limits=values)


def invite(org, email="pending@example.com", **kwargs):
    return OrganizationInvitation.objects.create(
        org=org,
        email=email,
        token_hash=uuid4().hex,
        expires_at=timezone.now() + timedelta(days=7),
        **kwargs,
    )


def test_new_organization_starts_with_agreed_limits():
    org = Org.objects.create(name="New account")
    org.refresh_from_db()
    assert org.usage_limits == {
        "users": 5,
        "contacts": 2500,
        "companies": 500,
        "deals": 500,
    }
    usage = organization_usage(org)
    for resource in ("tasks", "tickets", "appointments"):
        assert usage["limits"].get(resource) is None
    org.usage_limits["users"] = 10
    assert Org(name="Another account").usage_limits["users"] == 5


def test_existing_unlimited_and_custom_accounts_keep_their_limits():
    for limits in ({}, {"users": 2, "contacts": 100}):
        org = Org.objects.create(name="Existing account", usage_limits=limits)
        org.name = "Renamed account"
        org.save()
        org.refresh_from_db()
        assert org.usage_limits == limits


def test_only_platform_owner_can_change_limits(
    admin_user, admin_profile, admin_client, user_client, org_b
):
    url = f"/api/platform/organizations/{org_b.pk}/limits/"
    before = dict(org_b.usage_limits)
    payload = {"limits": {"users": 5, "contacts": 100, "tasks": 0}}
    for client in (APIClient(), admin_client, user_client):
        assert client.patch(url, payload, format="json").status_code == 403
    admin_user.is_superuser = True
    admin_user.save(update_fields=["is_superuser"])
    client = _make_authenticated_client(admin_user, admin_profile.org, admin_profile)
    response = client.patch(url, payload, format="json")
    assert response.status_code == 200, response.data
    assert response.data["limits"]["contacts"] == 100
    org_b.refresh_from_db()
    assert org_b.usage_limits == {**before, **payload["limits"]}
    audit = SecurityAuditLog.objects.get(event_type="ORGANIZATION_LIMITS_CHANGED")
    assert audit.user == admin_user and audit.org == org_b
    assert audit.metadata["after"] == org_b.usage_limits
    assert (
        client.patch(url, {"limits": {"contacts": None}}, format="json").status_code
        == 200
    )
    org_b.refresh_from_db()
    assert org_b.usage_limits["contacts"] is None and org_b.usage_limits["users"] == 5
    admin_user.is_superuser = False
    admin_user.save(update_fields=["is_superuser"])
    assert client.patch(url, payload, format="json").status_code == 403


@pytest.mark.parametrize("bad", [-1, 1.5, True, "10", 2147483648, {}, []])
def test_limit_input_is_strict(bad):
    from common.views.platform_usage_views import LimitsInput

    assert not LimitsInput(data={"limits": {"users": bad}}).is_valid()
    assert not LimitsInput(data={"limits": {"unknown": 2}}).is_valid()


@pytest.mark.parametrize("label,resource", RECORD_RESOURCES.items())
def test_each_object_limit_blocks_only_creation(
    label, resource, org_a, admin_profile, admin_user
):
    model = apps.get_model(label)
    fields = {"org": org_a}
    if resource == "contacts":
        fields["first_name"] = "Quota test"
    elif resource in ("tasks", "appointments"):
        fields["title"] = "Quota test"
    else:
        fields["name"] = "Quota test"
    if resource == "appointments":
        fields.update(
            host=admin_profile,
            created_by=admin_user,
            starts_at=timezone.now(),
            ends_at=timezone.now() + timedelta(hours=1),
        )
    limit(org_a, **{resource: 1})
    row = model.objects.create(**fields)
    with pytest.raises(OrganizationLimitReached):
        model.objects.create(**fields)
    assert resource_count(org_a.pk, resource) == 1
    limit(org_a, **{resource: 0})
    row.save()  # Lowering a limit never freezes existing records.
    row.delete()
    assert resource_count(org_a.pk, resource) == 0
    with pytest.raises(OrganizationLimitReached):
        model.objects.create(**fields)
    limit(org_a, **{resource: None})
    model.objects.create(**fields)


def test_counts_ignore_member_visibility_and_stale_dashboard(
    org_a, org_b, user_profile, regular_user
):
    limit(org_a, contacts=1)
    cache.clear()
    assert organization_usage(org_a)["contacts"] == 0
    Contact.objects.create(org=org_a, first_name="Other owner")
    with impersonate(regular_user), pytest.raises(OrganizationLimitReached):
        Contact.objects.create(org=org_a, first_name="Over quota")
    with rls_org(org_b):
        Contact.objects.create(org=org_b, first_name="Independent quota")


def test_bulk_create_is_atomic(org_a):
    limit(org_a, contacts=1)
    with pytest.raises(OrganizationLimitReached):
        Contact.objects.bulk_create(
            [Contact(org=org_a, first_name="One"), Contact(org=org_a, first_name="Two")]
        )
    assert Contact.objects.filter(org=org_a).count() == 0


def test_merged_contact_restoration_cannot_exceed_limit(org_a):
    contact = Contact.objects.create(
        org=org_a, first_name="Merged", merged_at=timezone.now()
    )
    limit(org_a, contacts=0)
    with pytest.raises(OrganizationLimitReached):
        Contact.all_objects.filter(pk=contact.pk).update(merged_at=None)
    contact.merged_at = None
    with pytest.raises(OrganizationLimitReached):
        contact.save(update_fields=["merged_at"])


def test_pending_invites_reserve_seats_and_resending_does_not_add(org_a):
    before = resource_count(org_a.pk, "users")
    limit(org_a, users=before + 1)
    invitation = invite(org_a)
    assert resource_count(org_a.pk, "users") == before + 1
    invitation.expires_at += timedelta(days=1)
    invitation.save()
    with pytest.raises(OrganizationLimitReached):
        invite(org_a, "second@example.com")
    invitation.revoked_at = timezone.now()
    invitation.save()
    assert resource_count(org_a.pk, "users") == before
    invite(org_a, "second@example.com")


def test_expired_invite_and_support_access_do_not_consume_seats(org_a):
    before = resource_count(org_a.pk, "users")
    limit(org_a, users=before)
    row = OrganizationInvitation.objects.create(
        org=org_a,
        email="expired@example.com",
        token_hash=uuid4().hex,
        expires_at=timezone.now() - timedelta(days=1),
    )
    support = User.objects.create_user("support-quota@example.com", None)
    Profile.objects.create(org=org_a, user=support, is_platform_access=True)
    assert resource_count(org_a.pk, "users") == before
    row.expires_at = timezone.now() + timedelta(days=1)
    with pytest.raises(OrganizationLimitReached):
        row.save()


def test_acceptance_consumes_reserved_seat_even_after_limit_is_lowered(org_a):
    before = resource_count(org_a.pk, "users")
    limit(org_a, users=before + 1)
    invitation = invite(org_a)
    limit(org_a, users=0)
    user = User.objects.create_user(invitation.email, None)
    Profile.objects.create(user=user, org=org_a)
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at"])
    assert resource_count(org_a.pk, "users") == before + 1


def test_reactivation_checked_for_save_and_queryset_update(org_a):
    user = User.objects.create_user("inactive-quota@example.com", None)
    profile = Profile.objects.create(user=user, org=org_a, is_active=False)
    limit(org_a, users=resource_count(org_a.pk, "users"))
    profile.is_active = True
    with pytest.raises(OrganizationLimitReached):
        profile.save()
    with pytest.raises(OrganizationLimitReached):
        Profile.objects.filter(pk=profile.pk).update(is_active=True)
    profile.refresh_from_db()
    assert not profile.is_active


def test_partial_reactivation_uses_persisted_support_flag(org_a):
    user = User.objects.create_user("partial-quota@example.com", None)
    profile = Profile.objects.create(user=user, org=org_a, is_active=False)
    limit(org_a, users=resource_count(org_a.pk, "users"))
    # Only is_active will reach the database; an unrelated in-memory flag
    # must not make this newly occupied seat look like support access.
    profile.is_platform_access = True
    profile.is_active = True
    with pytest.raises(OrganizationLimitReached):
        profile.save(update_fields=["is_active"])
    profile.refresh_from_db()
    assert not profile.is_active and not profile.is_platform_access


def test_profile_preferences_do_not_acquire_quota_lock(admin_profile):
    with patch("common.usage_limits.locked_quota") as lock:
        admin_profile.language = "es"
        admin_profile.save(update_fields=["language"])
    lock.assert_not_called()


def test_contact_import_exceeding_capacity_rolls_back_every_row(admin_client, org_a):
    from django.core.files.uploadedfile import SimpleUploadedFile

    limit(org_a, contacts=1)
    upload = SimpleUploadedFile(
        "quota.csv",
        b"first_name,email,phone\nFirst,first-quota@example.com,+12025550123\nSecond,second-quota@example.com,+12025550124\n",
        content_type="text/csv",
    )
    response = admin_client.post(
        "/api/contacts/import/commit/", {"file": upload}, format="multipart"
    )
    assert response.status_code == 409, response.data
    assert resource_count(org_a.pk, "contacts") == 0


def test_full_calendar_rolls_back_related_deal_and_sends_no_email(
    admin_client, admin_profile, org_a
):
    contact = Contact.objects.create(
        org=org_a, first_name="Quota attendee", source="META"
    )
    limit(org_a, appointments=0)
    with patch("common.views.sales_appointment_views.queue_appointment_emails") as send:
        response = admin_client.post(
            "/api/sales-appointments/",
            {
                "title": "Over capacity",
                "host": str(admin_profile.pk),
                "contact": str(contact.pk),
                "starts_at": "2026-11-10T13:00:00Z",
                "ends_at": "2026-11-10T14:00:00Z",
                "create_deal": True,
            },
            format="json",
        )
    assert response.status_code == 409, response.data
    assert response.data["resource"] == "appointments"
    assert resource_count(org_a.pk, "deals") == 0
    assert resource_count(org_a.pk, "appointments") == 0
    send.assert_not_called()


def test_full_account_cannot_send_new_invitation(admin_client, org_a):
    limit(org_a, users=resource_count(org_a.pk, "users"))
    with patch("common.views.invitation_views.send_invitation") as send:
        response = admin_client.post(
            "/api/invitations/", {"email": "blocked@example.com"}, format="json"
        )
    assert response.status_code == 409, response.data
    assert response.data["code"] == "organization_limit_reached"
    send.assert_not_called()
    assert not OrganizationInvitation.objects.filter(
        email="blocked@example.com"
    ).exists()


def test_member_cannot_use_hidden_records_to_bypass_quota(
    user_client, user_profile, org_a
):
    from common.rbac import ensure_default_roles

    user_profile.access_role = ensure_default_roles(org_a)[0]
    user_profile.save()
    Contact.objects.create(org=org_a, first_name="Not assigned to member")
    limit(org_a, contacts=1)
    response = user_client.post(
        "/api/contacts/",
        {
            "first_name": "Over quota",
            "email": "over-quota@example.com",
            "phone": "2125550123",
            "source": "META",
            "stage": "LEAD",
        },
        format="json",
    )
    assert response.status_code == 409, response.data
    assert resource_count(org_a.pk, "contacts") == 1


@pytest.mark.postgres_only
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("resource", ["contacts", "users"])
def test_simultaneous_creations_cannot_take_the_last_slot_twice(org_a, resource):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import connections

    from common.rls.context import org_context

    limit(org_a, **{resource: resource_count(org_a.pk, resource) + 1})
    before = resource_count(org_a.pk, resource)
    barrier = Barrier(2)

    def create(index):
        try:
            barrier.wait(timeout=10)
            with org_context(org_a.pk):
                if resource == "contacts":
                    Contact.objects.create(
                        org_id=org_a.pk, first_name=f"Concurrent {index}"
                    )
                else:
                    invite(org_a, email=f"concurrent-{index}@example.com")
            return "created"
        except OrganizationLimitReached:
            return "limited"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, range(2)))
    assert sorted(results) == ["created", "limited"]
    assert resource_count(org_a.pk, resource) == before + 1
