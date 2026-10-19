"""Permanent tenant deletion must not leave orphaned login credentials."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from common.audit_log import SecurityAuditLog
from common.models import (
    MagicLinkToken,
    Org,
    OrganizationClosure,
    OrganizationInvitation,
    PendingFileDeletion,
    Profile,
    User,
)
from common.organization_lifecycle import change_lifecycle
from common.organization_purge import purge_organization
from common.serializer import OrgAwareRefreshToken
from common.testing import rls_org
from common.views.invitation_views import digest


@pytest.fixture
def closing_org(org_a, admin_user, settings):
    settings.CRM_ORG_CLOSURE_ENABLED = True
    settings.CRM_ORG_PURGE_ENABLED = True
    admin_user.is_superuser = True
    admin_user.save(update_fields=["is_superuser"])
    return org_a, admin_user


def make_due(org, actor):
    change_lifecycle(org.pk, actor, "close")
    deadline = timezone.now() - timedelta(seconds=1)
    Org.objects.filter(pk=org.pk).update(deletion_due_at=deadline)
    OrganizationClosure.objects.filter(org_id=org.pk).update(deletion_due_at=deadline)


def test_purge_removes_credentials_and_allows_fresh_invitation(
    closing_org, regular_user, user_profile, org_b, settings
):
    org, actor = closing_org
    settings.CRM_LEGAL_VERSION = ""
    old_user_id = regular_user.pk
    email = regular_user.email
    token = OrgAwareRefreshToken.for_user_and_org(regular_user, org, user_profile)
    raw_refresh = str(token)
    MagicLinkToken.objects.create(
        email=email, token="obsolete-login-token", expires_at=timezone.now()
    )
    audit = SecurityAuditLog.objects.create(
        user=regular_user, event_type="LOGIN_SUCCESS", description=email
    )
    make_due(org, actor)
    assert purge_organization(org.pk)
    assert not User.objects.filter(pk=old_user_id).exists()
    assert not User.objects.filter(email__iexact=email).exists()
    assert not OutstandingToken.objects.filter(jti=token["jti"]).exists()
    assert not MagicLinkToken.objects.filter(email__iexact=email).exists()
    assert not SecurityAuditLog.objects.filter(pk=audit.pk).exists()
    client = APIClient()
    assert (
        client.post(
            "/api/auth/refresh-token/", {"refresh": raw_refresh}, format="json"
        ).status_code
        == 401
    )

    raw = "fresh-invitation-after-deletion-937452"
    Org.objects.filter(pk=org_b.pk).update(owner=actor)
    OrganizationInvitation.objects.create(
        org=org_b,
        email=email,
        role="ADMIN",
        grants_ownership=True,
        invited_by=actor,
        token_hash=digest(raw),
        expires_at=timezone.now() + timedelta(days=1),
    )
    preview = client.post(
        "/api/auth/password/invitation/", {"token": raw}, format="json"
    )
    assert preview.status_code == 200
    assert preview.data["existing_account"] is False
    response = client.post(
        "/api/auth/password/register/",
        {
            "invitation": raw,
            "email": email,
            "name": "New Owner",
            "password": "Fresh-account-password-9345!",
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    fresh_user = User.objects.get(email=email)
    assert fresh_user.pk != old_user_id
    assert fresh_user.check_password("Fresh-account-password-9345!")
    assert Profile.objects.get(user=fresh_user, org=org_b).setup_step == (
        Profile.SetupStep.PROFILE_ORGANIZATION
    )
    assert User.objects.filter(pk=actor.pk).exists()


@pytest.mark.parametrize("active", [True, False])
def test_purge_preserves_shared_identity_and_password(
    closing_org, regular_user, user_profile, org_b, active
):
    org, actor = closing_org
    with rls_org(org_b):
        membership = Profile.objects.create(
            user=regular_user, org=org_b, is_active=active
        )
    old_password = regular_user.password
    make_due(org, actor)
    assert purge_organization(org.pk)
    regular_user.refresh_from_db()
    assert regular_user.password == old_password
    assert Profile.objects.filter(pk=membership.pk).exists()


def test_purge_preserves_owner_of_another_org_without_membership(
    closing_org, regular_user, user_profile, org_b
):
    org, actor = closing_org
    Org.objects.filter(pk=org_b.pk).update(owner=regular_user)
    make_due(org, actor)
    assert purge_organization(org.pk)
    assert User.objects.filter(pk=regular_user.pk).exists()


def test_purge_deletes_sole_owner_even_without_membership(closing_org, regular_user):
    org, actor = closing_org
    Org.objects.filter(pk=org.pk).update(owner=regular_user)
    make_due(org, actor)
    assert purge_organization(org.pk)
    assert not User.objects.filter(pk=regular_user.pk).exists()


@pytest.mark.parametrize("privilege", ["is_staff", "is_superuser"])
def test_purge_preserves_platform_operators(
    closing_org, regular_user, user_profile, privilege
):
    org, actor = closing_org
    User.objects.filter(pk=regular_user.pk).update(**{privilege: True})
    make_due(org, actor)
    assert purge_organization(org.pk)
    assert User.objects.filter(pk=regular_user.pk).exists()


def test_recovery_period_preserves_credentials(closing_org, regular_user, user_profile):
    org, actor = closing_org
    original_password = regular_user.password
    change_lifecycle(org.pk, actor, "close")
    assert not purge_organization(org.pk)
    change_lifecycle(org.pk, actor, "reactivate")
    regular_user.refresh_from_db()
    assert regular_user.password == original_password
    assert Profile.objects.filter(pk=user_profile.pk).exists()


def test_user_purge_and_photo_outbox_roll_back_together(
    closing_org, regular_user, user_profile
):
    org, actor = closing_org
    regular_user.profile_image.save("purge-avatar.png", ContentFile(b"demo"))
    key = regular_user.profile_image.name
    user_id = regular_user.pk
    make_due(org, actor)
    with pytest.raises(RuntimeError), transaction.atomic():
        purge_organization(org.pk)
        raise RuntimeError("rollback")
    assert User.objects.filter(pk=user_id).exists()
    assert Org.objects.filter(pk=org.pk).exists()
    assert not PendingFileDeletion.objects.filter(name=key).exists()
    with patch("common.organization_purge.enqueue_cleanup"):
        assert purge_organization(org.pk)
    assert not User.objects.filter(pk=user_id).exists()
    assert PendingFileDeletion.objects.filter(name=key, org_id=org.pk).exists()
    assert purge_organization(org.pk)


def test_purge_does_not_sweep_unrelated_orphan_users(closing_org, regular_user):
    org, actor = closing_org
    make_due(org, actor)
    assert purge_organization(org.pk)
    assert User.objects.filter(pk=regular_user.pk).exists()
