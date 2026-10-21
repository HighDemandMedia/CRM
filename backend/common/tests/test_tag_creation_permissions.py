"""Tag creation grants must not imply catalog management or tenant access."""

import pytest
from rest_framework.exceptions import PermissionDenied

from accounts.models import Account
from common.models import CRMRole, Tags
from common.rbac import default_rules
from common.settings_access import can_create_tags
from contacts.models import Contact
from contacts.services.csv_import import commit_rows

pytestmark = pytest.mark.django_db


def assign(profile, allowed, name="Member", settings=None):
    scope = "team" if name == "Manager" else "own"
    rules = default_rules(scope)
    rules["tags"] = {"create": allowed}
    role = CRMRole.objects.create(
        org=profile.org,
        name=name,
        scope=scope,
        rules=rules,
        settings_access=settings or {},
    )
    profile.access_role = role
    profile.save()
    return role


@pytest.mark.parametrize("name", ["Member", "Manager", "Sales specialist"])
@pytest.mark.parametrize("allowed", [False, True])
def test_explicit_creation_without_settings(user_client, user_profile, name, allowed):
    assign(user_profile, allowed, name)
    listing = user_client.get("/api/tags/?compact=true")
    assert listing.data["can_create"] is allowed
    response = user_client.post("/api/tags/", {"name": "New label"}, format="json")
    assert response.status_code == (201 if allowed else 403), response.data
    assert (
        Tags.objects.filter(org=user_profile.org, name="New label").exists() is allowed
    )
    assert user_client.get("/api/tags/?include_archived=true").status_code == 403


def test_create_does_not_allow_modify_archive_or_reactivate(user_client, user_profile):
    assign(user_profile, True)
    tag = Tags.objects.create(org=user_profile.org, name="Protected", slug="protected")
    assert (
        user_client.put(
            f"/api/tags/{tag.pk}/", {"name": "Changed"}, format="json"
        ).status_code
        == 403
    )
    assert user_client.delete(f"/api/tags/{tag.pk}/").status_code == 403
    tag.is_active = False
    tag.save()
    assert (
        user_client.post("/api/tags/", {"name": "Protected"}, format="json").status_code
        == 403
    )
    tag.refresh_from_db()
    assert not tag.is_active


def test_explicit_denial_overrides_manager_catalog_management(
    user_client, user_profile
):
    assign(user_profile, False, "Manager", {"tags": "manage"})
    assert (
        user_client.post("/api/tags/", {"name": "Denied"}, format="json").status_code
        == 403
    )
    assert user_client.get("/api/tags/?include_archived=true").status_code == 200


def test_legacy_manager_grant_is_preserved_and_editable(admin_client, user_profile):
    role = assign(user_profile, True, "Manager", {"tags": "manage"})
    role.rules.pop("tags")
    role.save()
    assert can_create_tags(user_profile)
    response = admin_client.get("/api/roles/")
    row = next(r for r in response.data["roles"] if r["id"] == str(role.pk))
    assert row["rules"]["tags"]["create"] is True
    row["rules"]["tags"]["create"] = False
    response = admin_client.patch(
        f"/api/roles/{role.pk}/",
        {
            "name": "Manager",
            "scope": "team",
            "rules": row["rules"],
            "settings_access": {"tags": "manage"},
        },
        format="json",
    )
    assert response.status_code == 200, response.data
    user_profile.refresh_from_db()
    assert not can_create_tags(user_profile)


def test_cross_tenant_role_does_not_grant_creation(user_profile, org_b):
    role = assign(user_profile, True)
    role.org = org_b
    role.save()
    user_profile.refresh_from_db()
    assert not can_create_tags(user_profile)


def test_admin_retains_creation(admin_client):
    assert admin_client.get("/api/tags/?compact=true").data["can_create"] is True


def test_company_legacy_names_cannot_bypass_permission(user_client, user_profile):
    assign(user_profile, False)
    response = user_client.post(
        "/api/accounts/", {"name": "Blocked company", "tags": ["newtag"]}, format="json"
    )
    assert response.status_code == 403, response.data
    assert not Account.objects.filter(
        org=user_profile.org, name="Blocked company"
    ).exists()
    assert not Tags.objects.filter(org=user_profile.org, name="newtag").exists()


def test_import_cannot_create_tags_but_can_apply_existing(user_profile):
    assign(user_profile, False)
    csv = b"first_name,email,tags\nAlex,alex@example.com,Existing\nTaylor,taylor@example.com,New\n"
    Tags.objects.create(org=user_profile.org, name="Existing", slug="existing")
    with pytest.raises(PermissionDenied):
        commit_rows(csv, user_profile.org, user_profile)
    assert not Contact.objects.filter(
        org=user_profile.org, email="alex@example.com"
    ).exists()
    result = commit_rows(
        b"first_name,email,tags\nAlex,alex@example.com,Existing\n",
        user_profile.org,
        user_profile,
    )
    assert result["created"] == 1, result
    assert (
        Contact.objects.get(email="alex@example.com", org=user_profile.org)
        .tags.get()
        .name
        == "Existing"
    )


def test_role_grant_requires_boolean(admin_client):
    rules = default_rules()
    rules["tags"] = {"create": "true"}
    response = admin_client.post(
        "/api/roles/", {"name": "Invalid", "rules": rules}, format="json"
    )
    assert response.status_code == 400
