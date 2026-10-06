"""Interface language is a personal account preference, never tenant configuration."""

import pytest

from common.models import Profile

pytestmark = pytest.mark.django_db


def test_default_language_is_english(admin_client):
    assert admin_client.get("/api/profile/").json()["user_obj"]["ui_language"] == "en"
    assert admin_client.get("/api/org/ui-context/").json()["ui_language"] == "en"


@pytest.mark.parametrize("language", ["es", "en"])
def test_member_can_save_language(user_client, regular_user, language):
    response = user_client.patch(
        "/api/profile/", {"ui_language": language}, format="json"
    )
    assert response.status_code == 200
    regular_user.refresh_from_db()
    assert regular_user.ui_language == language
    assert user_client.get("/api/org/ui-context/").json()["ui_language"] == language


@pytest.mark.parametrize("language", ["fr", "ES", "", None, "es<script>"])
def test_reject_unsupported_language(user_client, regular_user, language):
    response = user_client.patch(
        "/api/profile/", {"ui_language": language}, format="json"
    )
    assert response.status_code == 400
    regular_user.refresh_from_db()
    assert regular_user.ui_language == "en"


def test_language_is_private_to_account(
    admin_client, user_client, admin_user, regular_user, admin_profile
):
    original_communication_language = admin_profile.language
    assert (
        admin_client.patch(
            "/api/profile/", {"ui_language": "es"}, format="json"
        ).status_code
        == 200
    )
    admin_user.refresh_from_db()
    regular_user.refresh_from_db()
    admin_profile.refresh_from_db()
    assert admin_user.ui_language == "es"
    assert regular_user.ui_language == "en"
    assert user_client.get("/api/org/ui-context/").json()["ui_language"] == "en"
    assert admin_profile.language == original_communication_language


def test_same_account_keeps_language_in_other_organization(
    admin_client, admin_user, org_b
):
    from common.testing import rls_org

    with rls_org(org_b):
        Profile.objects.create(user=admin_user, org=org_b, role="ADMIN")
    assert (
        admin_client.patch(
            "/api/profile/", {"ui_language": "es"}, format="json"
        ).status_code
        == 200
    )
    admin_user.refresh_from_db()
    with rls_org(org_b):
        assert Profile.objects.get(user=admin_user, org=org_b).user.ui_language == "es"


def test_language_update_cannot_change_another_user(
    admin_client, admin_user, regular_user
):
    response = admin_client.patch(
        "/api/profile/",
        {"ui_language": "es", "user_id": str(regular_user.id), "is_superuser": True},
        format="json",
    )
    assert response.status_code == 200
    regular_user.refresh_from_db()
    admin_user.refresh_from_db()
    assert regular_user.ui_language == "en"
    assert not regular_user.is_superuser
    assert admin_user.ui_language == "es"
