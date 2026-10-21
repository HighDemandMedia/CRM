"""Invitation setup is durable, membership-scoped, and cannot grant permissions."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from common.models import Org, OrganizationInvitation, Profile, User
from common.views.invitation_views import digest

pytestmark = pytest.mark.django_db

DETAILS = {
    "name": "Invited Person",
    "ui_language": "es",
    "timezone": "America/New_York",
    "complete_setup": True,
}
ORG_DETAILS = {
    "name": "Customer",
    "timezone": "America/New_York",
    "default_currency": "USD",
    "complete_setup": True,
}


def pending(profile, step):
    profile.setup_step = step
    profile.save(update_fields=["setup_step"])


def test_existing_memberships_do_not_require_setup(user_profile, user_client):
    assert user_profile.setup_step == Profile.SetupStep.COMPLETE
    assert user_client.get("/api/org/ui-context/").data["setup_step"] == "complete"


@pytest.mark.parametrize("new_user", [True, False])
def test_team_invitation_starts_profile_setup(
    new_user, user_client, regular_user, org_b, admin_user
):
    raw = "team-invitation-setup-token-982734"
    invitation = OrganizationInvitation.objects.create(
        org=org_b,
        email="new-invite@example.com" if new_user else regular_user.email,
        role="USER",
        invited_by=admin_user,
        token_hash=digest(raw),
        expires_at=timezone.now() + timedelta(days=1),
    )
    if new_user:
        response = APIClient().post(
            "/api/auth/password/register/",
            {
                "email": invitation.email,
                "name": "New User",
                "password": "Safe-invitation-password-9832!",
                "invitation": raw,
            },
            format="json",
        )
        assert response.status_code == 201, response.data
    else:
        response = user_client.post(
            "/api/auth/accept-invitation/", {"token": raw}, format="json"
        )
        assert response.status_code == 200, response.data
    profile = Profile.objects.get(org=org_b, user__email=invitation.email)
    assert profile.setup_step == Profile.SetupStep.PROFILE
    assert profile.role == "USER"


@pytest.mark.parametrize("existing_account", [False, True])
def test_super_admin_invitation_password_profile_and_organization_access(
    existing_account, admin_client, admin_user, org_a, org_b, regular_user
):
    """Exercise real invitation endpoints, including the second-membership case."""
    Org.objects.filter(pk=org_a.pk).update(owner=admin_user)
    email = "new-member@example.com"
    password = "Safe-invitation-password-9832!"
    if existing_account:
        # Existing identity belongs only to B before accepting A's invitation.
        Profile.objects.filter(user=regular_user).delete()
        Profile.objects.create(user=regular_user, org=org_b, role="USER")
        regular_user.set_password(password)
        regular_user.save(update_fields=["password"])
        email = regular_user.email
    unrelated = Org.objects.create(name="Unassigned organization")
    with patch("common.views.invitation_views.send_invitation") as send:
        invited = admin_client.post(
            "/api/invitations/", {"email": email, "role": "USER"}, format="json"
        )
    assert invited.status_code == 201, invited.data
    invitation, raw = send.call_args.args
    assert not invitation.grants_ownership
    client = APIClient()
    preview = client.post(
        "/api/auth/password/invitation/", {"token": raw}, format="json"
    )
    assert preview.status_code == 200, preview.data
    assert preview.data["existing_account"] is existing_account
    if existing_account:
        old_password = regular_user.password
        login = client.post(
            "/api/auth/password/login/",
            {"email": email, "password": password},
            format="json",
        )
        assert login.status_code == 200, login.data
        client.credentials(HTTP_AUTHORIZATION="Bearer " + login.data["access_token"])
        accepted = client.post(
            "/api/auth/accept-invitation/", {"token": raw}, format="json"
        )
        assert accepted.status_code == 200, accepted.data
        session = client.post(
            "/api/auth/switch-org/", {"org_id": str(org_a.pk)}, format="json"
        )
        regular_user.refresh_from_db()
        assert regular_user.password == old_password
    else:
        session = client.post(
            "/api/auth/password/register/",
            {
                "email": email,
                "name": "New Member",
                "password": password,
                "invitation": raw,
            },
            format="json",
        )
    assert session.status_code in (200, 201), session.data
    client.credentials(HTTP_AUTHORIZATION="Bearer " + session.data["access_token"])
    member = User.objects.get(email=email)
    assert member.check_password(password) and not member.is_superuser
    assert client.get("/api/org/ui-context/").data["setup_step"] == "profile"
    assert client.get("/api/profile/").status_code == 200
    assert client.get("/api/org/timezones/").status_code == 200
    saved = client.patch("/api/profile/", DETAILS, format="json")
    assert saved.status_code == 200, saved.data
    assert saved.data["setup_step"] == "complete"
    expected = {str(org_a.pk), str(org_b.pk)} if existing_account else {str(org_a.pk)}
    me = client.get("/api/auth/me/").data
    assert not me["is_platform_owner"]
    assert {row["id"] for row in me["organizations"]} == expected
    directory = client.get("/api/org/").data["profile_org_list"]
    assert {str(row["org"]["id"]) for row in directory} == expected
    assert (
        client.post(
            "/api/auth/switch-org/", {"org_id": str(unrelated.pk)}, format="json"
        ).status_code
        == 403
    )
    assert (
        client.patch("/api/org/settings/", ORG_DETAILS, format="json").status_code
        == 403
    )


def test_profile_confirmation_saves_preferences_and_only_own_membership(
    user_client, user_profile, regular_user, org_b
):
    other = Profile.objects.create(user=regular_user, org=org_b, setup_step="profile")
    pending(user_profile, Profile.SetupStep.PROFILE)
    response = user_client.patch(
        "/api/profile/",
        {**DETAILS, "role": "ADMIN", "setup_step": "organization"},
        format="json",
    )
    assert response.status_code == 200, response.data
    user_profile.refresh_from_db()
    regular_user.refresh_from_db()
    other.refresh_from_db()
    assert user_profile.setup_step == "complete"
    assert user_profile.role == "USER"
    assert user_profile.timezone == DETAILS["timezone"]
    assert regular_user.name == DETAILS["name"] and regular_user.ui_language == "es"
    assert other.setup_step == "profile"
    assert user_client.get("/api/org/ui-context/").data["setup_step"] == "complete"


@pytest.mark.parametrize(
    "values",
    [
        {**DETAILS, "name": "  "},
        {**DETAILS, "ui_language": "fr"},
        {**DETAILS, "timezone": "Invalid/Zone"},
        {"complete_setup": True},
    ],
)
def test_invalid_details_do_not_advance_or_partially_save(
    user_client, user_profile, regular_user, values
):
    pending(user_profile, Profile.SetupStep.PROFILE)
    original = regular_user.name
    response = user_client.patch("/api/profile/", values, format="json")
    assert response.status_code == 400
    user_profile.refresh_from_db()
    regular_user.refresh_from_db()
    assert user_profile.setup_step == "profile"
    assert regular_user.name == original


def test_regular_save_and_forged_step_do_not_skip_confirmation(
    user_client, user_profile
):
    pending(user_profile, Profile.SetupStep.PROFILE)
    response = user_client.patch(
        "/api/profile/", {"name": "Saved Name", "setup_step": "complete"}, format="json"
    )
    assert response.status_code == 200
    user_profile.refresh_from_db()
    assert user_profile.setup_step == "profile"


def test_initial_admin_completes_profile_then_organization(admin_client, admin_profile):
    pending(admin_profile, Profile.SetupStep.PROFILE_ORGANIZATION)
    assert (
        admin_client.patch("/api/org/settings/", ORG_DETAILS, format="json").status_code
        == 400
    )
    response = admin_client.patch("/api/profile/", DETAILS, format="json")
    assert response.status_code == 200, response.data
    assert response.data["setup_step"] == "organization"
    assert admin_client.get("/api/org/settings/").data["setup_step"] == "organization"
    assert (
        admin_client.patch(
            "/api/org/settings/", {"complete_setup": True}, format="json"
        ).status_code
        == 400
    )
    response = admin_client.patch("/api/org/settings/", ORG_DETAILS, format="json")
    assert response.status_code == 200, response.data
    admin_profile.refresh_from_db()
    assert admin_profile.setup_step == "complete"


def test_member_cannot_complete_organization_settings(user_client, user_profile):
    pending(user_profile, Profile.SetupStep.PROFILE)
    assert (
        user_client.patch("/api/org/settings/", ORG_DETAILS, format="json").status_code
        == 403
    )
    user_profile.refresh_from_db()
    assert user_profile.setup_step == "profile"
