"""Invitation setup is durable, membership-scoped, and cannot grant permissions."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from common.models import OrganizationInvitation, Profile
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
