"""Public authentication must never bypass the invitation boundary."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from common.models import MagicLinkToken, Org, OrganizationInvitation, Profile, User
from common.views.invitation_views import digest

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_throttles():
    cache.clear()


def test_recovery_does_not_send_to_or_create_unknown_user():
    with patch("common.tasks.send_magic_link_email.delay") as send:
        result = APIClient().post(
            "/api/auth/magic-link/request/",
            {"email": "unknown@example.com"},
            format="json",
        )
    assert result.status_code == 200
    send.assert_not_called()
    assert not MagicLinkToken.objects.exists()
    assert not User.objects.exists()


def test_previously_issued_magic_link_cannot_provision_an_account():
    raw = "a" * 64
    MagicLinkToken.objects.create(
        email="unknown@example.com",
        token=raw,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    result = APIClient().post(
        "/api/auth/magic-link/verify/", {"token": raw}, format="json"
    )
    assert result.status_code == 403
    assert not User.objects.exists()


def test_owner_creates_customer_and_customer_invites_team(admin_client, admin_user):
    admin_user.is_superuser = True
    admin_user.save()
    with patch("common.views.organization_views.send_invitation") as send:
        result = admin_client.post(
            "/api/org/",
            {"name": "Private Customer", "administrator_email": "customer@example.com"},
            format="json",
        )
    assert result.status_code == 200, result.data
    row, raw = send.call_args.args
    assert row.grants_ownership and row.role == "ADMIN"
    assert row.token_hash == digest(raw)
    assert not User.objects.filter(email=row.email).exists()
    accepted = APIClient().post(
        "/api/auth/password/register/",
        {
            "email": row.email,
            "name": "Customer Admin",
            "password": "Safe-private-password-921!",
            "invitation": raw,
        },
        format="json",
    )
    assert accepted.status_code == 201, accepted.data
    assert accepted.data["needs_organization_setup"]
    user = User.objects.get(email=row.email)
    profile = Profile.objects.get(user=user, org=row.org)
    assert profile.is_super_admin and not user.is_superuser
    assert profile.setup_step == Profile.SetupStep.PROFILE_ORGANIZATION
    customer = APIClient()
    customer.credentials(HTTP_AUTHORIZATION="Bearer " + accepted.data["access_token"])
    assert (
        customer.post("/api/org/", {"name": "Not Allowed"}, format="json").status_code
        == 403
    )
    with patch("common.views.invitation_views.send_mail") as mail:
        invited = customer.post(
            "/api/invitations/", {"email": "team@example.com"}, format="json"
        )
    assert invited.status_code == 201, invited.data
    assert not OrganizationInvitation.objects.get(
        email="team@example.com"
    ).grants_ownership
    assert "Accept invitation" in mail.call_args.kwargs["html_message"]
    assert not User.objects.filter(email="team@example.com").exists()


def test_non_owner_cannot_create_customer(admin_client):
    result = admin_client.post(
        "/api/org/",
        {"name": "No Grant", "administrator_email": "customer@example.com"},
        format="json",
    )
    assert result.status_code == 403
    assert not Org.objects.filter(name="No Grant").exists()


def test_legacy_create_user_queues_invitation_instead_of_granting_access(admin_client):
    with patch("common.views.invitation_views.send_mail"):
        result = admin_client.post(
            "/api/users/",
            {"email": "legacy-new@example.com", "role": "USER"},
            format="json",
        )
    assert result.status_code == 201, result.data
    assert OrganizationInvitation.objects.filter(
        email="legacy-new@example.com"
    ).exists()
    assert not User.objects.filter(email="legacy-new@example.com").exists()


def test_failed_delivery_preserves_customer_invitation_for_resend(
    admin_client, admin_user
):
    admin_user.is_superuser = True
    admin_user.save()
    with patch(
        "common.views.organization_views.send_invitation",
        side_effect=OSError("offline"),
    ):
        result = admin_client.post(
            "/api/org/",
            {"name": "Retry Customer", "administrator_email": "retry@example.com"},
            format="json",
        )
    assert result.status_code == 200
    assert result.data["invitation_warning"]
    assert OrganizationInvitation.objects.get(
        email="retry@example.com"
    ).grants_ownership


def test_owner_can_still_create_own_workspace_without_admin_email(
    admin_client, admin_user
):
    admin_user.is_superuser = True
    admin_user.save()
    result = admin_client.post("/api/org/", {"name": "My Workspace"}, format="json")
    assert result.status_code == 200, result.data
    assert Org.objects.get(name="My Workspace").owner_id == admin_user.pk
    assert not OrganizationInvitation.objects.filter(org__name="My Workspace").exists()


def test_existing_customer_acceptance_hands_off_ownership_and_requests_setup(
    admin_client, admin_user, user_client, regular_user
):
    admin_user.is_superuser = True
    admin_user.save()
    with patch("common.views.organization_views.send_invitation") as send:
        result = admin_client.post(
            "/api/org/",
            {"name": "Existing Customer", "administrator_email": regular_user.email},
            format="json",
        )
    assert result.status_code == 200
    invitation, raw = send.call_args.args
    response = user_client.post(
        "/api/auth/accept-invitation/", {"token": raw}, format="json"
    )
    assert response.status_code == 200, response.data
    assert response.data["needs_organization_setup"]
    assert Org.objects.get(pk=invitation.org_id).owner_id == regular_user.pk
    assert (
        Profile.objects.get(org=invitation.org, user=regular_user).setup_step
        == Profile.SetupStep.PROFILE_ORGANIZATION
    )


def test_team_cannot_forge_owner_grant(admin_client, org_a):
    with patch("common.views.invitation_views.send_mail"):
        response = admin_client.post(
            "/api/invitations/",
            {"email": "team@example.com", "role": "USER", "grants_ownership": True},
            format="json",
        )
    assert response.status_code == 201
    assert not OrganizationInvitation.objects.get(
        email="team@example.com"
    ).grants_ownership


def test_invalid_initial_owner_invitation_rolls_back_new_account(admin_user, org_a):
    raw = "invalid-owner-grant-test-token"
    row = OrganizationInvitation.objects.create(
        org=org_a,
        email="newowner@example.com",
        role="ADMIN",
        invited_by=admin_user,
        grants_ownership=True,
        token_hash=digest(raw),
        expires_at=timezone.now() + timedelta(days=1),
    )
    response = APIClient().post(
        "/api/auth/password/register/",
        {
            "email": row.email,
            "name": "New Owner",
            "password": "Safe-private-password-921!",
            "invitation": raw,
        },
        format="json",
    )
    assert response.status_code == 400
    assert not User.objects.filter(email=row.email).exists()
    row.refresh_from_db()
    assert row.accepted_at is None
