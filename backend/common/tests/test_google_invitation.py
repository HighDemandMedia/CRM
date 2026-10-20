"""Google enrollment must consume a valid invitation without a CRM password."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from common.models import LegalAcceptance, Org, OrganizationInvitation, Profile, User
from common.views.invitation_views import digest

pytestmark = pytest.mark.django_db
RAW = "google-invitation-registration-928374"
EMAIL = "new-google-invite@gmail.com"
URL = "/api/auth/google/callback/"


@pytest.fixture(autouse=True)
def google(settings):
    cache.clear()
    settings.GOOGLE_CLIENT_ID = "test-client"
    settings.GOOGLE_CLIENT_SECRET = "test-only"
    settings.CRM_LEGAL_VERSION = "test-version"
    with (
        patch("common.views.auth_views.requests.post") as exchange,
        patch("google.oauth2.id_token.verify_oauth2_token") as verify,
    ):
        exchange.return_value.status_code = 200
        exchange.return_value.json.return_value = {"id_token": "verified-by-provider"}
        verify.return_value = {
            "email": EMAIL,
            "email_verified": True,
            "name": "Google Invitee",
        }
        yield verify
    cache.clear()


def invite(org, **values):
    return OrganizationInvitation.objects.create(
        org=org,
        email=EMAIL,
        role="USER",
        token_hash=digest(RAW),
        expires_at=timezone.now() + timedelta(days=1),
        **values,
    )


def post(**values):
    return APIClient().post(
        URL,
        {
            "code": "test-code",
            "code_verifier": "test-verifier",
            "redirect_uri": "https://crm.example.com/login",
            "invitation": RAW,
            "legal_version": "test-version",
            "legal_locale": "en",
            "accept_terms": True,
            **values,
        },
        format="json",
    )


def test_new_member_gets_only_invited_membership_and_onboarding(org_a, org_b):
    invitation = invite(org_a)
    response = post(
        role="ADMIN",
        org_id=str(org_b.pk),
        name="Untrusted name",
        email="fake@gmail.com",
    )
    assert response.status_code == 200, response.data
    user = User.objects.get(email=EMAIL)
    assert user.name == "Google Invitee"
    assert not user.has_usable_password()
    assert not user.is_superuser
    profile = Profile.objects.get(user=user)
    assert profile.org_id == org_a.pk
    assert profile.role == "USER"
    assert profile.setup_step == Profile.SetupStep.PROFILE
    assert response.data["current_org"]["id"] == str(org_a.pk)
    assert response.data["invitation_accepted"] is True
    assert LegalAcceptance.objects.filter(
        user=user, org=org_a, version="test-version"
    ).exists()
    invitation.refresh_from_db()
    assert invitation.accepted_at
    assert post().status_code == 400
    assert Profile.objects.filter(user=user).count() == 1


def test_owner_invitation_starts_profile_and_organization_setup(org_a, admin_user):
    admin_user.is_superuser = True
    admin_user.save(update_fields=["is_superuser"])
    Org.objects.filter(pk=org_a.pk).update(owner=admin_user)
    invitation = invite(org_a, grants_ownership=True, invited_by=admin_user)
    invitation.role = "ADMIN"
    invitation.save(update_fields=["role"])
    response = post(organization_authority=True)
    assert response.status_code == 200, response.data
    user = User.objects.get(email=EMAIL)
    org_a.refresh_from_db()
    assert org_a.owner_id == user.pk
    assert (
        Profile.objects.get(user=user, org=org_a).setup_step
        == Profile.SetupStep.PROFILE_ORGANIZATION
    )
    assert not user.is_superuser


@pytest.mark.parametrize(
    "state",
    [
        "expired",
        "revoked",
        "accepted",
        "inactive",
        "closing",
        "wrong_email",
        "unverified",
        "untrusted",
        "missing",
        "bad_signature",
    ],
)
def test_invalid_invitation_or_google_identity_never_creates_account(
    state, org_a, google
):
    invitation = invite(org_a)
    if state == "expired":
        invitation.expires_at = timezone.now() - timedelta(seconds=1)
    if state == "revoked":
        invitation.revoked_at = timezone.now()
    if state == "accepted":
        invitation.accepted_at = timezone.now()
    if state == "inactive":
        Org.objects.filter(pk=org_a.pk).update(is_active=False)
    if state == "closing":
        Org.objects.filter(pk=org_a.pk).update(closing_at=timezone.now())
    if state == "wrong_email":
        google.return_value["email"] = "other@gmail.com"
    if state == "unverified":
        google.return_value["email_verified"] = False
    if state == "untrusted":
        google.return_value["email"] = "external@example.com"
    if state == "bad_signature":
        google.side_effect = ValueError("Invalid signature")
    invitation.save()
    response = post(**({"invitation": ""} if state == "missing" else {}))
    assert response.status_code in (400, 403), response.data
    assert "access_token" not in response.data
    assert not User.objects.filter(email=EMAIL).exists()


@pytest.mark.parametrize(
    "values",
    [
        {"accept_terms": False},
        {"accept_terms": "true"},
        {"legal_version": "old"},
        {"legal_locale": "bad"},
    ],
)
def test_explicit_current_terms_are_required(values, org_a):
    invitation = invite(org_a)
    assert post(**values).status_code == 400
    assert not User.objects.filter(email=EMAIL).exists()
    invitation.refresh_from_db()
    assert invitation.accepted_at is None


def test_owner_must_accept_on_behalf_of_organization(org_a, admin_user):
    invitation = invite(org_a, grants_ownership=True, invited_by=admin_user)
    assert post().status_code == 400
    assert not User.objects.filter(email=EMAIL).exists()
    invitation.refresh_from_db()
    assert invitation.accepted_at is None


def test_existing_google_user_keeps_password_and_other_membership(org_a, org_b):
    user = User.objects.create_user(
        EMAIL, "Existing-password-27398!", name="Existing Name"
    )
    Profile.objects.create(user=user, org=org_b, role="USER")
    password = user.password
    invite(org_a)
    response = post()
    assert response.status_code == 200, response.data
    assert response.data["current_org"]["id"] == str(org_a.pk)
    assert Profile.objects.filter(user=user).count() == 2
    user.refresh_from_db()
    assert user.password == password
    assert user.name == "Existing Name"


def test_disabled_user_cannot_accept_or_be_reactivated(org_a):
    user = User.objects.create_user(EMAIL, None, is_active=False)
    invitation = invite(org_a)
    assert post().status_code == 403
    user.refresh_from_db()
    invitation.refresh_from_db()
    assert not user.is_active
    assert invitation.accepted_at is None
    assert not Profile.objects.filter(user=user).exists()


def test_existing_inactive_membership_is_not_reactivated(org_a):
    user = User.objects.create_user(EMAIL, None)
    profile = Profile.objects.create(user=user, org=org_a, role="USER", is_active=False)
    invite(org_a)
    assert post().status_code == 400
    profile.refresh_from_db()
    assert not profile.is_active


def test_invalid_owner_handoff_rolls_back_user_and_membership(org_a, admin_user):
    invitation = invite(org_a, grants_ownership=True, invited_by=admin_user)
    invitation.role = "ADMIN"
    invitation.save(update_fields=["role"])
    assert post(organization_authority=True).status_code == 400
    assert not User.objects.filter(email=EMAIL).exists()
    invitation.refresh_from_db()
    assert invitation.accepted_at is None
