"""Settings access remains independent of organization-wide record grants."""

import pytest

from common.models import CRMRole
from common.rbac import default_rules

pytestmark = pytest.mark.django_db


@pytest.fixture
def broad_member(user_profile):
    user_profile.access_role = CRMRole.objects.create(
        org=user_profile.org,
        name="Organization records",
        scope="organization",
        rules=default_rules("organization"),
    )
    user_profile.save()
    return user_profile


@pytest.mark.parametrize(
    "path",
    [
        "/api/roles/",
        "/api/teams/",
        "/api/invitations/",
        "/api/custom-fields/?catalog=true&target_model=Contact",
    ],
)
def test_record_scope_does_not_open_admin_settings(user_client, broad_member, path):
    assert user_client.get(path).status_code == 403


@pytest.mark.parametrize(
    "path",
    [
        "/api/org/settings/",
        "/api/pipeline-settings/",
        "/api/tags/?include_archived=true",
        "/api/webforms/",
    ],
)
def test_member_cannot_read_settings(user_client, broad_member, path):
    assert user_client.get(path).status_code == 403


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("patch", "/api/org/settings/", {"name": "Forbidden change"}),
        ("post", "/api/tags/", {"name": "Forbidden tag"}),
        ("post", "/api/webforms/", {}),
        ("post", "/api/roles/", {"name": "Forbidden role"}),
        ("post", "/api/custom-fields/", {}),
        ("post", "/api/teams/", {"name": "Forbidden team"}),
    ],
)
def test_direct_writes_still_require_admin(
    user_client, broad_member, method, path, payload
):
    assert getattr(user_client, method)(path, payload, format="json").status_code == 403


def test_settings_access_changes_without_reissuing_token(admin_client, admin_profile):
    assert admin_client.get("/api/org/ui-context/").data["permissions"]["is_admin"]
    # This fixture is an ordinary administrator, not the protected organization owner.
    admin_profile.role = "USER"
    admin_profile.save()
    assert not admin_client.get("/api/org/ui-context/").data["permissions"]["is_admin"]
    assert admin_client.get("/api/roles/").status_code == 403


@pytest.fixture
def manager(user_profile):
    role = CRMRole.objects.create(
        org=user_profile.org, name="Manager", scope="team", rules=default_rules("team")
    )
    user_profile.access_role = role
    user_profile.save()
    return role


@pytest.mark.parametrize(
    "section,path,method,payload",
    [
        (
            "organization",
            "/api/org/settings/",
            "patch",
            {"name": "Updated organization"},
        ),
        ("tags", "/api/tags/?include_archived=true", "post", {"name": "Manager tag"}),
        (
            "properties",
            "/api/custom-fields/?catalog=true&target_model=Contact",
            "post",
            {},
        ),
        ("pipelines", "/api/pipeline-settings/", "put", {}),
        ("forms", "/api/webforms/", "post", {}),
    ],
)
def test_manager_requires_explicit_read_and_manage(
    user_client, manager, section, path, method, payload
):
    assert user_client.get(path).status_code == 403
    manager.settings_access = {section: "read"}
    manager.save()
    assert user_client.get(path).status_code == 200
    assert getattr(user_client, method)(path, payload, format="json").status_code == 403
    manager.settings_access = {section: "manage"}
    manager.save()
    result = getattr(user_client, method)(path, payload, format="json")
    # Empty mutation payloads reach validation, not an authorization bypass.
    assert result.status_code in (200, 201, 400), result.data
    manager.settings_access = {}
    manager.save()
    assert user_client.get(path).status_code == 403


def test_manager_cannot_delegate_or_manage_members(user_client, manager):
    manager.settings_access = {
        k: "manage"
        for k in (
            "organization",
            "properties",
            "pipelines",
            "tags",
            "forms",
            "roles",
            "team",
        )
    }
    manager.save()
    for path in ("/api/roles/", "/api/teams/", "/api/invitations/"):
        assert user_client.get(path).status_code == 403
    assert (
        user_client.patch(f"/api/roles/{manager.pk}/", {}, format="json").status_code
        == 403
    )


def test_only_admin_can_grant_manager_settings(admin_client, user_client, manager):
    payload = {
        "name": "Manager",
        "scope": "team",
        "rules": default_rules("team"),
        "settings_access": {"tags": "manage"},
    }
    assert (
        user_client.patch(
            f"/api/roles/{manager.pk}/", payload, format="json"
        ).status_code
        == 403
    )
    assert (
        admin_client.patch(
            f"/api/roles/{manager.pk}/", payload, format="json"
        ).status_code
        == 200
    )
    assert (
        user_client.get("/api/permissions/me/").data["settings_access"]["tags"]
        == "manage"
    )
    assert (
        user_client.post("/api/tags/", {"name": "Delegated"}, format="json").status_code
        == 201
    )
    payload["settings_access"] = {}
    assert (
        admin_client.patch(
            f"/api/roles/{manager.pk}/", payload, format="json"
        ).status_code
        == 200
    )
    assert (
        user_client.post("/api/tags/", {"name": "Revoked"}, format="json").status_code
        == 403
    )


@pytest.mark.parametrize(
    "name,grants",
    [
        ("Member", {"tags": "manage"}),
        ("Custom", {"organization": "read"}),
        ("Manager", {"roles": "manage"}),
        ("Manager", {"tags": True}),
        ("Manager", ["tags"]),
    ],
)
def test_invalid_or_non_manager_grants_rejected(admin_client, name, grants):
    scope = "team" if name == "Manager" else "own"
    result = admin_client.post(
        "/api/roles/",
        {
            "name": name,
            "scope": scope,
            "rules": default_rules(scope),
            "settings_access": grants,
        },
        format="json",
    )
    assert result.status_code == 400


def test_runtime_configuration_available_without_settings(user_client, broad_member):
    tags = user_client.get("/api/tags/")
    assert tags.status_code == 200
    assert "totals" not in tags.data
    fields = user_client.get("/api/custom-fields/?target_model=Contact")
    assert fields.status_code == 200
    assert fields.data["totals"] is None
    context = user_client.get("/api/org/ui-context/")
    assert context.status_code == 200
    assert context.data["pipelines"]
    assert set(context.data["permissions"]["settings_access"].values()) == {"none"}


def test_grants_do_not_cross_tenants_or_apply_to_ordinary_roles(
    user_profile, broad_member, manager, org_b
):
    from common.settings_access import settings_access

    manager.settings_access = {"organization": "manage"}
    manager.org = org_b
    manager.save()
    user_profile.refresh_from_db()
    assert settings_access(user_profile)["organization"] == "none"
    manager.org = user_profile.org
    manager.name = "Custom Manager"
    manager.save()
    user_profile.refresh_from_db()
    assert settings_access(user_profile)["organization"] == "none"


def test_manager_can_save_granted_pipeline_and_properties(
    admin_client, user_client, manager
):
    manager.settings_access = {"pipelines": "manage", "properties": "manage"}
    manager.save()
    config = user_client.get("/api/pipeline-settings/").json()
    stages = config["pipelines"]["Contact"]["stages"]
    stages[0]["label"] = "Delegated stage"
    response = user_client.put(
        "/api/pipeline-settings/",
        {"target_model": "Contact", "revision": config["revision"], "stages": stages},
        format="json",
    )
    assert response.status_code == 200, response.data
    response = user_client.post(
        "/api/custom-fields/",
        {
            "target_model": "Contact",
            "key": "delegated_field",
            "label": "Delegated field",
            "field_type": "text",
        },
        format="json",
    )
    assert response.status_code == 201, response.data


def test_manager_webforms_read_manage_and_tenant_isolation(user_client, manager, org_b):
    from common.testing import rls_org
    from webforms.models import WebForm

    form = WebForm.objects.create(org=manager.org, name="Own form")
    with rls_org(org_b):
        foreign = WebForm.objects.create(org=org_b, name="Foreign form")
    manager.settings_access = {"forms": "read"}
    manager.save()
    assert user_client.get(f"/api/webforms/{form.pk}/").status_code == 200
    assert user_client.get(f"/api/webforms/{foreign.pk}/").status_code == 404
    assert user_client.get(f"/api/webforms/{form.pk}/submissions/").status_code == 403
    manager.settings_access = {"forms": "manage"}
    manager.save()
    assert user_client.get(f"/api/webforms/{form.pk}/submissions/").status_code == 200
    assert user_client.delete(f"/api/webforms/{foreign.pk}/").status_code == 404
