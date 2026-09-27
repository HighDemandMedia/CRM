from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from common.models import Org, OrganizationInvitation, Profile, User
from common.serializer import OrgAwareRefreshToken
from common.views.invitation_views import digest

pytestmark = pytest.mark.django_db
PASSWORD = "A-safe-testing-password-9824!"
BASE = "/api/auth/password/"


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


def register(**overrides):
    values = dict(
        email="owner@example.com",
        password=PASSWORD,
        name="Organization Owner",
        organization="Password Test",
        timezone="America/New_York",
    )
    return APIClient().post(BASE + "register/", values | overrides, format="json")


def test_registration_creates_separate_org_and_creator_not_platform_admin():
    response = register(role="ADMIN", is_superuser=True)
    assert response.status_code == 201, response.data
    user = User.objects.get(email="owner@example.com")
    assert user.check_password(PASSWORD) and user.password != PASSWORD
    assert not user.is_superuser and not user.is_staff
    org = Org.objects.get(created_by=user)
    assert org.timezone == "America/New_York"
    assert Profile.objects.get(org=org, user=user).is_super_admin
    assert AccessToken(response.data["access_token"])["org_id"] == str(org.pk)


@pytest.mark.parametrize(
    "values",
    [
        {"name": ""},
        {"organization": ""},
        {"password": "1234567890"},
        {"password": "short"},
        {"timezone": "Not/AZone"},
    ],
)
def test_invalid_registration_is_atomic(values):
    assert register(**values).status_code == 400
    assert not User.objects.filter(email="owner@example.com").exists()


def test_existing_identity_cannot_be_claimed_or_have_password_overwritten():
    user = User.objects.create_user("Owner@Example.com", PASSWORD, name="Existing")
    assert register(password="Another-strong-password-828!").status_code == 400
    user.refresh_from_db()
    assert user.check_password(PASSWORD)
    assert not Org.objects.filter(name="Password Test").exists()


def test_password_login_and_disabled_user():
    register()
    client = APIClient()
    response = client.post(
        BASE + "login/",
        {"email": "OWNER@example.com", "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["current_org"]["name"] == "Password Test"
    wrong = client.post(
        BASE + "login/",
        {"email": "owner@example.com", "password": "wrong"},
        format="json",
    )
    missing = client.post(
        BASE + "login/",
        {"email": "missing@example.com", "password": "wrong"},
        format="json",
    )
    assert (
        wrong.status_code == missing.status_code == 401 and wrong.data == missing.data
    )
    User.objects.filter(email="owner@example.com").update(is_active=False)
    assert (
        client.post(
            BASE + "login/",
            {"email": "owner@example.com", "password": PASSWORD},
            format="json",
        ).status_code
        == 401
    )


def test_login_does_not_select_org_from_untrusted_input():
    register()
    other = Org.objects.create(name="Another Organization")
    result = APIClient().post(
        BASE + "login/",
        {"email": "owner@example.com", "password": PASSWORD, "org_id": str(other.pk)},
        format="json",
    )
    assert AccessToken(result.data["access_token"])["org_id"] != str(other.pk)


def test_multiple_memberships_require_selection_and_revoked_membership_is_excluded():
    register()
    user = User.objects.get(email="owner@example.com")
    other = Org.objects.create(name="Second Organization")
    profile = Profile.objects.create(org=other, user=user)
    client = APIClient()
    body = {"email": user.email, "password": PASSWORD}
    result = client.post(BASE + "login/", body, format="json")
    assert result.data["current_org"] is None and len(result.data["organizations"]) == 2
    profile.is_active = False
    profile.save()
    result = client.post(BASE + "login/", body, format="json")
    assert len(result.data["organizations"]) == 1


def test_invitation_grants_only_the_invited_org_and_role():
    org = Org.objects.create(name="Inviting Organization")
    raw = "secure-invitation-test-token-982347"
    invitation = OrganizationInvitation.objects.create(
        org=org,
        email="owner@example.com",
        role="USER",
        token_hash=digest(raw),
        expires_at=timezone.now() + timedelta(days=1),
    )
    result = register(invitation=raw, organization="Ignored", role="ADMIN")
    assert result.status_code == 201, result.data
    profile = Profile.objects.get(user__email="owner@example.com")
    assert (
        profile.org_id == org.pk
        and profile.role == "USER"
        and not profile.is_super_admin
    )
    from conftest import rls_org

    with rls_org(org):
        assert profile.access_role.name == "Member"
    invitation.refresh_from_db()
    assert invitation.accepted_at
    assert not Org.objects.filter(name="Ignored").exists()


def test_invalid_invitation_never_creates_an_account():
    assert register(invitation="invalid-token").status_code == 400
    assert not User.objects.filter(email="owner@example.com").exists()


def test_password_change_requires_old_password_and_retires_refresh_token():
    original = register().data
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer " + original["access_token"])
    assert client.get(BASE + "change/").data["has_password"]
    new = "My-new-testing-password-8439!"
    assert (
        client.post(BASE + "change/", {"password": new}, format="json").status_code
        == 400
    )
    response = client.post(
        BASE + "change/", {"password": new, "current_password": PASSWORD}, format="json"
    )
    assert response.status_code == 200, response.data
    assert User.objects.get(email="owner@example.com").check_password(new)
    assert client.get(BASE + "change/").status_code == 401
    assert (
        APIClient()
        .post(
            "/api/auth/refresh-token/",
            {"refresh": original["refresh_token"]},
            format="json",
        )
        .status_code
        == 401
    )


def test_existing_passwordless_user_can_set_password_in_authenticated_session():
    user = User.objects.create_user("legacy@example.com", name="Legacy User")
    token = OrgAwareRefreshToken.for_user_and_org(user, None)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer " + str(token.access_token))
    assert (
        client.post(BASE + "change/", {"password": PASSWORD}, format="json").status_code
        == 200
    )


def test_expired_recovery_proof_cannot_reset_password():
    register()
    user = User.objects.get(email="owner@example.com")
    token = OrgAwareRefreshToken.for_user_and_org(user, None)
    token["password_reset_until"] = int(timezone.now().timestamp()) - 1
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer " + str(token.access_token))
    assert (
        client.post(BASE + "change/", {"password": PASSWORD}, format="json").status_code
        == 400
    )


def test_verified_recovery_session_can_reset_without_old_password():
    register()
    user = User.objects.get(email="owner@example.com")
    token = OrgAwareRefreshToken.for_user_and_org(user, None)
    token["password_reset_until"] = int(timezone.now().timestamp()) + 600
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer " + str(token.access_token))
    assert (
        client.post(
            BASE + "change/",
            {"password": "Recovered-safe-password-987!"},
            format="json",
        ).status_code
        == 200
    )


def test_failed_logins_are_throttled():
    client = APIClient()
    for _ in range(10):
        assert (
            client.post(
                BASE + "login/",
                {"email": "missing@example.com", "password": "wrong"},
                format="json",
            ).status_code
            == 401
        )
    assert (
        client.post(
            BASE + "login/",
            {"email": "missing@example.com", "password": "wrong"},
            format="json",
        ).status_code
        == 429
    )


def test_registration_can_be_closed(settings):
    settings.PASSWORD_REGISTRATION_ENABLED = False
    assert register().status_code == 403


def test_real_email_recovery_survives_refresh_and_changes_password():
    import secrets

    from common.models import MagicLinkToken

    register()
    raw = secrets.token_hex(32)
    MagicLinkToken.objects.create(
        email="owner@example.com",
        token=raw,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    client = APIClient()
    verified = client.post(
        "/api/auth/magic-link/verify/", {"token": raw}, format="json"
    )
    assert verified.status_code == 200, verified.data
    refreshed = client.post(
        "/api/auth/refresh-token/",
        {"refresh": verified.data["refresh_token"]},
        format="json",
    )
    assert refreshed.status_code == 200, refreshed.data
    client.credentials(HTTP_AUTHORIZATION="Bearer " + refreshed.data["access"])
    assert client.get(BASE + "change/").data["can_reset_password"]
    assert (
        client.post(
            BASE + "change/",
            {"password": "Email-recovered-password-9324!"},
            format="json",
        ).status_code
        == 200
    )


def test_profile_password_status_does_not_consume_attempt_limit():
    original = register().data
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer " + original["access_token"])
    for _ in range(12):
        assert client.get(BASE + "change/").status_code == 200
