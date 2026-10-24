from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from rest_framework.test import APIClient

from common.models import Org, Profile, User
from common.platform_access import accessible_profiles, support_context
from common.serializer import OrgAwareRefreshToken
from common.testing import _make_authenticated_client, rls_org
from contacts.models import Contact
from tasks.models import Task

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner(admin_user, admin_profile):
    admin_user.is_superuser = True
    admin_user.is_staff = True
    admin_user.save()
    return (
        admin_user,
        admin_profile,
        _make_authenticated_client(admin_user, admin_profile.org, admin_profile),
    )


def test_customer_super_admin_is_not_platform_owner(
    admin_user, admin_profile, admin_client, org_a
):
    Org.objects.filter(pk=org_a.pk).update(owner=admin_user)
    admin_profile.refresh_from_db()
    token = OrgAwareRefreshToken.for_user_and_org(admin_user, org_a, admin_profile)
    assert token["is_super_admin"]
    assert not token["is_platform_owner"] and not token["can_preview"]
    assert admin_client.get("/api/leads/").status_code == 404
    for path in (
        "/api/webforms/",
        "/api/contacts/",
        "/api/tags/",
        "/api/roles/",
        "/api/pipeline-settings/",
    ):
        assert admin_client.get(path).status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/api/invoices/",
        "/api/cases/routing-rules/",
        "/api/cases/mailboxes/",
        "/api/org/tokens/",
    ],
)
def test_customer_cannot_open_preview_by_url(admin_client, path):
    assert admin_client.get(path).status_code == 404


def test_owner_directory_without_preview(owner, org_b):
    user, profile, client = owner
    assert not OrgAwareRefreshToken.for_user_and_org(user, profile.org, profile)[
        "can_preview"
    ]
    assert client.get("/api/leads/").status_code == 404
    directory = client.get("/api/org/").json()["profile_org_list"]
    assert str(org_b.pk) in [row["org"]["id"] for row in directory]
    me = client.get("/api/auth/me/").json()
    assert me["is_platform_owner"]
    assert str(org_b.pk) in [row["id"] for row in me["organizations"]]


def test_owner_explicit_switch_preserves_tenant_owner_and_isolation(
    owner, org_b, profile_b
):
    user, profile, client = owner
    Org.objects.filter(pk=org_b.pk).update(owner=profile_b.user)
    with rls_org(org_b):
        contact = Contact.objects.create(org=org_b, first_name="Customer secret")
    assert client.get(f"/api/contacts/{contact.pk}/").status_code == 404
    response = client.post(
        "/api/auth/switch-org/", {"org_id": str(org_b.pk)}, format="json"
    )
    assert response.status_code == 200, response.content
    support = Profile.objects.get(user=user, org=org_b)
    assert support.is_platform_access and support.role == "ADMIN"
    assert not support.is_super_admin
    client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access_token"])
    assert client.get(f"/api/contacts/{contact.pk}/").status_code == 200
    assert client.get("/api/leads/").status_code == 404
    org_b.refresh_from_db()
    assert org_b.owner_id == profile_b.user_id


def test_customer_cannot_switch_or_enumerate_others(admin_client, org_b):
    assert (
        admin_client.post(
            "/api/auth/switch-org/", {"org_id": str(org_b.pk)}, format="json"
        ).status_code
        == 403
    )
    assert str(org_b.pk) not in str(admin_client.get("/api/org/").json())
    assert (
        admin_client.post("/api/org/", {"name": "Extra"}, format="json").status_code
        == 403
    )


def test_platform_visit_loads_customer_context_and_team_day(owner, org_b, profile_b):
    user, home_profile, client = owner
    with rls_org(org_b):
        task = Task.objects.create(
            org=org_b,
            created_by=profile_b.user,
            title="Customer follow-up",
            due_date=timezone.localdate(),
            status="New",
        )
        task.assigned_to.add(profile_b)
    with rls_org(home_profile.org):
        Task.objects.create(
            org=home_profile.org,
            created_by=user,
            title="Platform private task",
            due_date=timezone.localdate(),
            status="New",
        )
    response = client.post(
        "/api/auth/switch-org/", {"org_id": str(org_b.pk)}, format="json"
    )
    assert response.status_code == 200
    client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access_token"])
    # The current configuration wins even if the switch token predates an edit.
    Org.objects.filter(pk=org_b.pk).update(
        name="Customer workspace", default_currency="GBP"
    )
    context = client.get("/api/org/ui-context/").data
    assert context["organization"] == {
        "id": str(org_b.pk),
        "name": "Customer workspace",
        "currency": "GBP",
    }
    assert context["is_platform_owner"] and context["permissions"]["is_admin"]
    assert context["platform_access"]["return_organization"] == {
        "id": str(home_profile.org_id),
        "name": home_profile.org.name,
    }
    support = Profile.objects.get(org=org_b, user=user)
    day = client.get("/api/dashboard/day-summary/").data
    assert day["selected_user"] == "all"
    assert day["current_user"] == str(support.pk)
    assert [row["id"] for row in day["tasks"]] == [str(task.pk)]
    assert (
        client.get("/api/dashboard/day-summary/", {"user": str(support.pk)}).data[
            "tasks"
        ]
        == []
    )
    # Switching back restores the owner's own membership and personal day.
    response = client.post(
        "/api/auth/switch-org/", {"org_id": str(home_profile.org_id)}, format="json"
    )
    assert response.status_code == 200
    client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access_token"])
    assert client.get("/api/org/ui-context/").data["platform_access"] is None
    day = client.get("/api/dashboard/day-summary/").data
    assert day["selected_user"] == str(home_profile.pk)
    assert [row["name"] for row in day["tasks"]] == ["Platform private task"]


def test_customer_has_no_support_context(admin_client):
    assert admin_client.get("/api/org/ui-context/").data["platform_access"] is None


def test_support_return_excludes_disabled_and_support_memberships(owner, org_b):
    user, home, client = owner
    client.post("/api/auth/switch-org/", {"org_id": str(org_b.pk)}, format="json")
    support = Profile.objects.get(user=user, org=org_b)
    home.is_active = False
    home.save()
    assert support_context(support) == {"return_organization": None}
    user.is_superuser = False
    user.save()
    support.refresh_from_db()
    assert support_context(support) is None


def test_support_return_prefers_owned_workspace(owner, org_b):
    user, home, client = owner
    Org.objects.filter(pk=home.org_id).update(owner=user)
    alternative = Org.objects.create(name="Another membership")
    Profile.objects.create(user=user, org=alternative)
    client.post("/api/auth/switch-org/", {"org_id": str(org_b.pk)}, format="json")
    support = Profile.objects.get(user=user, org=org_b)
    assert support_context(support)["return_organization"]["id"] == str(home.org_id)


def test_revoked_platform_access_fails_with_old_access_and_refresh_tokens(owner, org_b):
    user, _, client = owner
    result = client.post(
        "/api/auth/switch-org/", {"org_id": str(org_b.pk)}, format="json"
    ).data
    user.is_superuser = False
    user.save()
    client.credentials(HTTP_AUTHORIZATION="Bearer " + result["access_token"])
    assert client.get("/api/contacts/").status_code == 403
    assert (
        client.post(
            "/api/auth/refresh-token/",
            {"refresh": result["refresh_token"]},
            format="json",
        ).status_code
        == 403
    )
    assert not accessible_profiles(user).filter(org=org_b).exists()


def test_customer_cannot_modify_platform_owner(owner, org_b, profile_b):
    user, _, client = owner
    Org.objects.filter(pk=org_b.pk).update(owner=profile_b.user)
    client.post("/api/auth/switch-org/", {"org_id": str(org_b.pk)}, format="json")
    support = Profile.objects.get(user=user, org=org_b)
    customer = _make_authenticated_client(profile_b.user, org_b, profile_b)
    assert (
        customer.patch(
            f"/api/user/{user.pk}/", {"name": "Hijack"}, format="json"
        ).status_code
        == 403
    )
    assert (
        customer.post(
            f"/api/user/{user.pk}/status/", {"status": "Inactive"}, format="json"
        ).status_code
        == 403
    )
    assert (
        customer.post(
            f"/api/roles/members/{support.pk}/", {"role_id": "USER"}, format="json"
        ).status_code
        == 403
    )
    assert (
        customer.post(
            f"/api/members/{support.pk}/remove/",
            {"token": "invalid", "confirmation": user.email},
            format="json",
        ).status_code
        == 403
    )
    user.refresh_from_db()
    assert user.is_superuser and user.is_active


def provision(email="customer@example.com", **kwargs):
    output = StringIO()
    with patch(
        "common.management.commands.provision_crm_account.getpass",
        side_effect=["A-unique-long-passphrase!92"] * 2,
    ):
        call_command(
            "provision_crm_account",
            email=email,
            organization="Independent customer",
            name="Customer Owner",
            stdout=output,
            **kwargs,
        )
    return output.getvalue()


def test_private_customer_creation_is_separate_and_password_login_works(settings):
    settings.PASSWORD_REGISTRATION_ENABLED = False
    assert "Organization Super Admin" in provision()
    user = User.objects.get(email="customer@example.com")
    profile = Profile.objects.get(user=user)
    assert profile.is_super_admin and not profile.is_demo
    assert not user.is_superuser and not user.is_staff
    assert profile.org.timezone == "America/New_York"
    client = APIClient()
    result = client.post(
        "/api/auth/password/login/",
        {"email": user.email, "password": "A-unique-long-passphrase!92"},
        format="json",
    )
    assert result.status_code == 200
    assert str(profile.org_id) == result.data["current_org"]["id"]


def test_private_owner_creation():
    assert "Platform owner" in provision("owner@example.com", platform_owner=True)
    user = User.objects.get(email="owner@example.com")
    assert user.is_superuser and user.is_staff
    assert Profile.objects.get(user=user).is_super_admin
    with pytest.raises(CommandError):
        provision("second@example.com", platform_owner=True)
    assert not User.objects.filter(email="second@example.com").exists()


def test_existing_account_is_never_promoted_or_password_reset(admin_user):
    old_password = admin_user.password
    with pytest.raises(CommandError):
        provision(admin_user.email, platform_owner=True)
    admin_user.refresh_from_db()
    assert not admin_user.is_superuser and admin_user.password == old_password


def test_password_confirmation_failure_writes_nothing():
    with patch(
        "common.management.commands.provision_crm_account.getpass",
        side_effect=["A-unique-long-passphrase!92", "different"],
    ):
        with pytest.raises(CommandError):
            call_command(
                "provision_crm_account",
                email="bad@example.com",
                organization="No creation",
                name="Bad",
            )
    assert not Org.objects.filter(name="No creation").exists()
    assert not User.objects.filter(email="bad@example.com").exists()


def test_owner_cannot_switch_to_disabled_org(owner, org_b):
    org_b.is_active = False
    org_b.save()
    assert (
        owner[2]
        .post("/api/auth/switch-org/", {"org_id": str(org_b.pk)}, format="json")
        .status_code
        == 403
    )


def test_customer_cannot_assign_platform_flags(admin_client, admin_user, admin_profile):
    admin_client.patch(
        f"/api/user/{admin_user.pk}/",
        {
            "is_superuser": True,
            "is_staff": True,
            "is_platform_owner": True,
            "is_platform_access": True,
            "can_preview": True,
        },
        format="json",
    )
    admin_user.refresh_from_db()
    admin_profile.refresh_from_db()
    assert not admin_user.is_superuser and not admin_user.is_staff
    assert not admin_profile.is_platform_access
    assert admin_client.get("/api/leads/").status_code == 404


def test_preview_requires_owner_even_without_selected_organization(admin_user):
    token = OrgAwareRefreshToken.for_user_and_org(admin_user, None)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer " + str(token.access_token))
    assert client.get("/api/packs/").status_code == 404


def test_org_key_never_borrows_platform_privileges(owner, org_b, profile_b):
    owner[2].post("/api/auth/switch-org/", {"org_id": str(org_b.pk)}, format="json")
    client = APIClient()
    client.credentials(HTTP_TOKEN=org_b.api_key)
    assert client.get("/api/leads/").status_code == 404
    assert client.get("/api/contacts/").status_code == 200


def test_search_excludes_preview_records(admin_client, org_a):
    from leads.models import Lead

    Lead.objects.create(org=org_a, title="Preview secret", first_name="Preview")
    Contact.objects.create(org=org_a, first_name="Preview contact")
    results = admin_client.get("/api/search/?q=Preview").json()["results"]
    assert any(row["type"] == "contact" for row in results)
    assert not any(row["type"] == "lead" for row in results)


def test_weak_password_is_rejected_without_writes():
    with patch(
        "common.management.commands.provision_crm_account.getpass",
        return_value="password",
    ):
        with pytest.raises(CommandError):
            call_command(
                "provision_crm_account",
                email="weak@example.com",
                name="Weak",
                organization="Weak org",
            )
    assert not User.objects.filter(email="weak@example.com").exists()
