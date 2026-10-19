from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from common.models import MagicLinkToken, Org, Profile, User
from common.password_reset import send_password_reset_email
from common.serializer import OrgAwareRefreshToken

pytestmark = pytest.mark.django_db
BASE = "/api/auth/password/"
PASSWORD = "Original-testing-password-9837!"
NEW_PASSWORD = "Replacement-testing-password-8274!"


@pytest.fixture(autouse=True)
def reset_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user():
    user = User(email="recovery@example.com", name="Recovery Demo", is_active=True)
    user.set_password(PASSWORD)
    user.save()
    return user


def reset_body(user):
    return {
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "token": default_token_generator.make_token(user),
        "password": NEW_PASSWORD,
        "password_confirm": NEW_PASSWORD,
    }


def confirm(body):
    return APIClient().post(BASE + "reset/confirm/", body, format="json")


def test_request_is_generic_and_queues_unknown_addresses(user):
    with patch(
        "common.views.password_reset_views.send_password_reset_email.delay"
    ) as queue:
        results = [
            APIClient().post(BASE + "reset/request/", {"email": email}, format="json")
            for email in [user.email, "unknown@example.com"]
        ]
        assert results[0].data == results[1].data
        assert [r.status_code for r in results] == [200, 200]
        assert queue.call_count == 2


def test_mail_uses_trusted_url_and_ignores_unknown_or_disabled_users(
    user, settings, mailoutbox
):
    settings.FRONTEND_URL = "https://crm.example.test"
    send_password_reset_email(user.email, "es")
    assert len(mailoutbox) == 1
    assert (
        "https://crm.example.test/login/reset?uid="
        in mailoutbox[0].alternatives[0].content
    )
    assert "Restablece" in mailoutbox[0].subject
    send_password_reset_email("missing@example.com")
    user.is_active = False
    user.save()
    send_password_reset_email(user.email)
    assert len(mailoutbox) == 1


def test_reset_is_single_use_revokes_sessions_and_does_not_sign_in(
    user, django_capture_on_commit_callbacks
):
    tokens = OrgAwareRefreshToken.for_user_and_org(user, None)
    access = str(tokens.access_token)
    magic = MagicLinkToken.objects.create(
        email=user.email,
        token="old-recovery-link",
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    body = reset_body(user)
    with patch("common.password_reset.send_password_changed_email.delay") as queue:
        with django_capture_on_commit_callbacks(execute=True):
            response = confirm(body)
        assert response.status_code == 200, response.data
        queue.assert_called_once()
    assert "access_token" not in response.data and "refresh_token" not in response.data
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    with pytest.raises(TokenError):
        RefreshToken(str(tokens))
    with pytest.raises(AuthenticationFailed):
        JWTAuthentication().get_user(AccessToken(access))
    magic.refresh_from_db()
    assert magic.is_used
    assert confirm(body).status_code == 400


@pytest.mark.parametrize(
    "case", ["expired", "invalid", "wrong_user", "disabled", "mismatch", "weak", "jwt"]
)
def test_invalid_reset_preserves_password(user, case):
    body = reset_body(user)
    if case == "expired":
        with patch.object(
            default_token_generator,
            "_now",
            return_value=default_token_generator._now() - timedelta(hours=1),
        ):
            body["token"] = default_token_generator.make_token(user)
    elif case == "invalid":
        body["token"] = "invalid"
    elif case == "wrong_user":
        body["uid"] = "not-an-account"
    elif case == "disabled":
        user.is_active = False
        user.save()
    elif case == "mismatch":
        body["password_confirm"] = "Something-different!"
    elif case == "weak":
        body["password"] = body["password_confirm"] = "123456789012"
    elif case == "jwt":
        body["token"] = str(OrgAwareRefreshToken.for_user_and_org(user, None))
    response = confirm(body)
    assert response.status_code == 400, response.data
    user.refresh_from_db()
    assert user.check_password(PASSWORD)


def test_reset_request_rate_limit(user):
    with patch("common.views.password_reset_views.send_password_reset_email.delay"):
        for _ in range(5):
            assert (
                APIClient()
                .post(BASE + "reset/request/", {"email": user.email}, format="json")
                .status_code
                == 200
            )
        assert (
            APIClient()
            .post(BASE + "reset/request/", {"email": user.email}, format="json")
            .status_code
            == 429
        )


@pytest.mark.parametrize("remember,seconds", [(False, 8 * 3600), (True, 14 * 86400)])
def test_login_and_refresh_preserve_absolute_session(user, remember, seconds):
    response = APIClient().post(
        BASE + "login/",
        {"email": user.email, "password": PASSWORD, "remember_me": remember},
        format="json",
    )
    assert response.status_code == 200
    refresh = RefreshToken(response.data["refresh_token"])
    deadline = refresh["session_expires_at"]
    assert abs(deadline - timezone.now().timestamp() - seconds) < 3
    assert refresh["remember_me"] is remember
    result = APIClient().post(
        "/api/auth/refresh-token/",
        {"refresh": str(refresh), "remember_me": not remember},
        format="json",
    )
    assert result.status_code == 200, result.data
    rotated = RefreshToken(result.data["refresh"])
    assert rotated["exp"] == deadline
    assert rotated["remember_me"] is remember


def test_switch_and_short_remaining_access_keep_deadline(user):
    org = Org.objects.create(name="Session test")
    profile = Profile.objects.create(user=user, org=org)
    token = OrgAwareRefreshToken.for_user_and_org(user, org, profile, remember_me=False)
    token["session_expires_at"] = token["exp"] = int(timezone.now().timestamp()) + 60
    access = token.access_token
    assert access["exp"] == token["exp"]
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    result = client.post(
        "/api/auth/switch-org/", {"org_id": str(org.pk)}, format="json"
    )
    assert result.status_code == 200, result.data
    replacement = RefreshToken(result.data["refresh_token"])
    assert replacement["exp"] == token["exp"] and replacement["remember_me"] is False


def test_expired_session_cannot_be_reissued(user):
    with pytest.raises(TokenError):
        OrgAwareRefreshToken.for_user_and_org(
            user, None, session={"session_expires_at": 1}
        )
