from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from common.models import LegalAcceptance, Org, OrganizationInvitation, Profile, User
from common.views.invitation_views import digest

pytestmark = pytest.mark.django_db
TOKEN = "legal-invitation-test-token-123456"
VERSION = "2026-10-12"
CONSENT = {"legal_version": VERSION, "legal_locale": "es", "accept_terms": True}


@pytest.fixture(autouse=True)
def legal_enabled(settings):
    settings.CRM_LEGAL_VERSION = VERSION
    cache.clear()


@pytest.fixture
def invitation(org_b, regular_user, admin_user):
    return OrganizationInvitation.objects.create(
        org=org_b,
        email=regular_user.email,
        role="USER",
        invited_by=admin_user,
        token_hash=digest(TOKEN),
        expires_at=timezone.now() + timedelta(days=1),
    )


@pytest.mark.parametrize(
    "consent",
    [
        {},
        {**CONSENT, "accept_terms": False},
        {**CONSENT, "accept_terms": "true"},
        {**CONSENT, "legal_version": "old"},
        {**CONSENT, "legal_locale": "fr"},
    ],
)
def test_existing_invitee_must_accept_current_terms(user_client, invitation, consent):
    response = user_client.post(
        "/api/auth/accept-invitation/", {"token": TOKEN, **consent}, format="json"
    )
    assert response.status_code == 400
    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert not Profile.objects.filter(
        org=invitation.org, user__email=invitation.email
    ).exists()
    assert not LegalAcceptance.objects.exists()


def test_preview_exposes_server_requirements_without_accepting(user_client, invitation):
    response = user_client.post(
        "/api/auth/accept-invitation/", {"token": TOKEN, "preview": True}, format="json"
    )
    assert response.status_code == 200
    assert response.data["legal"] == {
        "version": VERSION,
        "organization_authority_required": False,
    }
    assert not LegalAcceptance.objects.exists()


@pytest.mark.parametrize("new_user", [False, True])
@pytest.mark.parametrize("owner", [False, True])
def test_both_invitation_paths_record_verified_receipt(
    user_client, invitation, new_user, owner
):
    if owner:
        invitation.invited_by.is_superuser = True
        invitation.invited_by.save(update_fields=["is_superuser"])
        Org.objects.filter(pk=invitation.org_id).update(owner=invitation.invited_by)
        invitation.org.refresh_from_db()
    invitation.grants_ownership = owner
    invitation.role = "ADMIN" if owner else "USER"
    if new_user:
        invitation.email = "new-legal@example.com"
    invitation.save()
    payload = {**CONSENT, "organization_authority": owner}
    if new_user:
        response = APIClient().post(
            "/api/auth/password/register/",
            {
                **payload,
                "invitation": TOKEN,
                "name": "Invited User",
                "email": invitation.email,
                "password": "Safe-testing-pass-91273!",
            },
            format="json",
        )
        assert response.status_code == 201, response.data
    else:
        response = user_client.post(
            "/api/auth/accept-invitation/", {"token": TOKEN, **payload}, format="json"
        )
        assert response.status_code == 200, response.data
    receipt = LegalAcceptance.objects.get()
    invitation.refresh_from_db()
    assert receipt.user.email == invitation.email
    assert receipt.org == invitation.org
    assert receipt.version == VERSION and receipt.locale == "es"
    assert receipt.on_behalf_of_organization == owner
    assert receipt.accepted_at <= invitation.accepted_at


def test_initial_admin_requires_authority(user_client, invitation):
    invitation.grants_ownership = True
    invitation.role = "ADMIN"
    invitation.save()
    response = user_client.post(
        "/api/auth/accept-invitation/", {"token": TOKEN, **CONSENT}, format="json"
    )
    assert response.status_code == 400
    assert not LegalAcceptance.objects.exists()


def test_register_without_acceptance_does_not_create_user(invitation):
    invitation.email = "new-legal@example.com"
    invitation.save()
    response = APIClient().post(
        "/api/auth/password/register/",
        {
            "invitation": TOKEN,
            "name": "New User",
            "email": invitation.email,
            "password": "Safe-testing-pass-91273!",
        },
        format="json",
    )
    assert response.status_code == 400
    assert not User.objects.filter(email=invitation.email).exists()


def test_acceptance_failure_rolls_back_membership(user_client, invitation):
    with patch(
        "common.legal.LegalAcceptance.objects.create",
        side_effect=RuntimeError("write failed"),
    ):
        with pytest.raises(RuntimeError):
            user_client.post(
                "/api/auth/accept-invitation/",
                {"token": TOKEN, **CONSENT},
                format="json",
            )
    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert not Profile.objects.filter(
        org=invitation.org, user__email=invitation.email
    ).exists()


def test_feature_waits_for_published_version(settings, user_client, invitation):
    settings.CRM_LEGAL_VERSION = ""
    response = user_client.post(
        "/api/auth/accept-invitation/", {"token": TOKEN}, format="json"
    )
    assert response.status_code == 200
    assert not LegalAcceptance.objects.exists()


def test_wrong_user_cannot_accept_or_create_receipt(admin_client, invitation):
    response = admin_client.post(
        "/api/auth/accept-invitation/", {"token": TOKEN, **CONSENT}, format="json"
    )
    assert response.status_code == 403
    assert not LegalAcceptance.objects.exists()
