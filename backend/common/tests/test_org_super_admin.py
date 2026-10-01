import pytest

from common.models import Org, Profile
from common.rbac import default_rules
from common.serializer import ProfileSerializer

pytestmark = pytest.mark.django_db


@pytest.fixture
def creator(org_a, admin_profile):
    Org.objects.filter(pk=org_a.pk).update(owner_id=admin_profile.user_id)
    org_a.refresh_from_db()
    admin_profile.refresh_from_db()
    return admin_profile


def test_creator_is_super_admin_only_in_owned_org(creator, org_b):
    assert creator.is_super_admin
    assert ProfileSerializer(creator).data["is_super_admin"] is True
    other = Profile.objects.create(org=org_b, user=creator.user, role="ADMIN")
    assert not other.is_super_admin


def test_admin_cannot_change_or_deactivate_creator(
    creator, user_client, regular_user, org_a
):
    colleague = Profile.objects.get(org=org_a, user=regular_user)
    colleague.role = "ADMIN"
    colleague.save()
    assert (
        user_client.post(
            f"/api/roles/members/{creator.pk}/", {"role_id": "ADMIN"}, format="json"
        ).status_code
        == 403
    )
    assert (
        user_client.patch(
            f"/api/user/{creator.user_id}/", {"role": "USER"}, format="json"
        ).status_code
        == 403
    )
    assert user_client.delete(f"/api/user/{creator.user_id}/").status_code == 403
    assert (
        user_client.post(
            f"/api/user/{creator.user_id}/status/",
            {"status": "Inactive"},
            format="json",
        ).status_code
        == 403
    )
    creator.refresh_from_db()
    assert creator.role == "ADMIN" and creator.is_active


def test_creator_can_assign_normal_admin(
    creator, admin_client, user_client, regular_user, org_a
):
    member = Profile.objects.get(org=org_a, user=regular_user)
    response = admin_client.post(
        f"/api/roles/members/{member.pk}/", {"role_id": "ADMIN"}, format="json"
    )
    assert response.status_code == 200, response.data
    member.refresh_from_db()
    assert member.role == "ADMIN" and not member.is_super_admin
    assert (
        admin_client.post(
            f"/api/roles/members/{member.pk}/",
            {"role_id": "SUPER_ADMIN"},
            format="json",
        ).status_code
        == 400
    )


def test_new_organization_creator_is_protected(admin_client, admin_user):
    admin_user.is_superuser = True
    admin_user.save()
    response = admin_client.post(
        "/api/org/", {"name": "New owner organization"}, format="json"
    )
    assert response.status_code in (200, 201), response.data
    org = Org.objects.get(name="New owner organization")
    member = Profile.objects.get(org=org, user=admin_user)
    assert org.owner_id == admin_user.pk and member.is_super_admin


def test_super_admin_is_not_a_custom_role(admin_client):
    response = admin_client.post(
        "/api/roles/", {"name": "Super Admin", "rules": default_rules()}, format="json"
    )
    assert response.status_code == 400
