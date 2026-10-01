import pytest
from rest_framework.exceptions import ValidationError

from common.models import CRMRole, Profile, Teams
from common.rbac import default_rules, scoped, validate_rules
from contacts.models import Contact

pytestmark = pytest.mark.django_db


def assign(profile, scope="own", **overrides):
    rules = default_rules(scope)
    rules["contacts"].update(overrides)
    role = CRMRole.objects.create(org=profile.org, name="Test role", rules=rules)
    profile.access_role = role
    profile.save()
    return role


def test_non_admin_cannot_manage_roles(user_client):
    assert user_client.get("/api/roles/").status_code == 403
    assert (
        user_client.post(
            "/api/roles/", {"name": "Escalate", "rules": default_rules()}, format="json"
        ).status_code
        == 403
    )


def test_invalid_permission_expansion_rejected():
    rules = default_rules()
    rules["contacts"]["delete"] = "organization"
    with pytest.raises(ValidationError):
        validate_rules(rules)


def test_own_team_and_organization_scopes(
    user_client, regular_user, org_a, admin_profile
):
    member = Profile.objects.get(org=org_a, user=regular_user)
    role = assign(member)
    own = Contact.objects.create(org=org_a, first_name="Mine", created_by=regular_user)
    own.assigned_to.add(member)
    teammate = Contact.objects.create(
        org=org_a, first_name="Team", created_by=admin_profile.user
    )
    teammate.assigned_to.add(admin_profile)
    Contact.objects.create(org=org_a, first_name="Other")
    assert set(scoped(Contact.objects.all(), member).values_list("pk", flat=True)) == {
        own.pk
    }
    team = Teams.objects.create(org=org_a, name="Sales")
    team.users.add(member, admin_profile)
    role.rules = default_rules("team")
    role.save()
    member.refresh_from_db()
    assert set(scoped(Contact.objects.all(), member).values_list("pk", flat=True)) == {
        own.pk,
        teammate.pk,
    }
    role.rules = default_rules("organization")
    role.save()
    member.refresh_from_db()
    assert scoped(Contact.objects.all(), member).count() == 3


def test_role_enforced_on_list_detail_and_writes(
    user_client, regular_user, org_a, admin_profile
):
    member = Profile.objects.get(org=org_a, user=regular_user)
    assign(member, create=False, edit="none", delete="none", export="none")
    own = Contact.objects.create(org=org_a, first_name="Mine", created_by=regular_user)
    other = Contact.objects.create(
        org=org_a, first_name="Other", created_by=admin_profile.user
    )
    assert user_client.get("/api/contacts/").status_code == 200
    assert user_client.get(f"/api/contacts/{other.pk}/").status_code in (403, 404)
    assert (
        user_client.patch(
            f"/api/contacts/{own.pk}/", {"first_name": "Changed"}, format="json"
        ).status_code
        == 403
    )
    assert user_client.delete(f"/api/contacts/{own.pk}/").status_code == 403
    assert user_client.post("/api/contacts/", {}, format="json").status_code == 403
    assert user_client.get("/api/roles/export/contacts/").status_code == 403


def test_role_assignment_rejects_cross_org_and_self(
    admin_client, admin_profile, profile_b, org_b
):
    from conftest import rls_org

    with rls_org(org_b):
        role = CRMRole.objects.create(org=org_b, name="Other", rules=default_rules())
    assert (
        admin_client.post(
            f"/api/roles/members/{admin_profile.pk}/",
            {"role_id": str(role.pk)},
            format="json",
        ).status_code
        == 400
    )
    assert (
        admin_client.post(
            f"/api/roles/members/{profile_b.pk}/",
            {"role_id": str(role.pk)},
            format="json",
        ).status_code
        == 404
    )


def test_manager_can_open_and_edit_teammates_contact(
    user_client, regular_user, org_a, admin_profile
):
    member = Profile.objects.get(org=org_a, user=regular_user)
    assign(member, "team")
    team = Teams.objects.create(org=org_a, name="Sales")
    team.users.add(member, admin_profile)
    contact = Contact.objects.create(
        org=org_a, first_name="Team member", created_by=admin_profile.user
    )
    contact.assigned_to.add(admin_profile)
    assert user_client.get(f"/api/contacts/{contact.pk}/").status_code == 200
    result = user_client.patch(
        f"/api/contacts/{contact.pk}/", {"first_name": "Updated"}, format="json"
    )
    assert result.status_code == 200, result.data


def test_view_scope_can_be_broader_than_edit_and_export(
    user_client, regular_user, org_a, admin_profile
):
    member = Profile.objects.get(org=org_a, user=regular_user)
    assign(member, "organization", edit="own", delete="none", export="own")
    own = Contact.objects.create(org=org_a, first_name="Mine", created_by=regular_user)
    other = Contact.objects.create(
        org=org_a, first_name="Other", created_by=admin_profile.user
    )
    assert user_client.get(f"/api/contacts/{other.pk}/").status_code == 200
    assert (
        user_client.patch(
            f"/api/contacts/{other.pk}/", {"first_name": "No"}, format="json"
        ).status_code
        == 403
    )
    own.assigned_to.add(member)
    data = user_client.get("/api/contacts/?permission_action=export").data
    assert str(own.pk) in str(data)
    assert str(other.pk) not in str(data)


def test_user_cannot_delete_through_confirmation_endpoint(
    user_client, regular_user, org_a
):
    member = Profile.objects.get(org=org_a, user=regular_user)
    assign(member, delete="none")
    contact = Contact.objects.create(
        org=org_a, first_name="Keep", created_by=regular_user
    )
    contact.assigned_to.add(member)
    response = user_client.get(f"/api/record-delete/contact/{contact.pk}/")
    assert response.status_code == 403
    assert Contact.objects.filter(pk=contact.pk).exists()


@pytest.mark.parametrize(
    "root,module",
    [
        ("contacts", "contacts"),
        ("accounts", "companies"),
        ("opportunities", "deals"),
        ("tasks", "tasks"),
        ("cases", "tickets"),
    ],
)
def test_no_access_blocks_every_core_module(
    user_client, regular_user, org_a, root, module
):
    member = Profile.objects.get(org=org_a, user=regular_user)
    role = assign(member)
    role.rules[module] = {
        "view": "none",
        "create": False,
        "edit": "none",
        "delete": "none",
        "export": "none",
    }
    role.save()
    assert user_client.get(f"/api/{root}/").status_code == 403
    assert user_client.post(f"/api/{root}/", {}, format="json").status_code == 403
    assert user_client.get(f"/api/roles/export/{module}/").status_code == 403


def test_ticket_csv_requires_export_permission(user_client, regular_user, org_a):
    member = Profile.objects.get(org=org_a, user=regular_user)
    role = assign(member)
    role.rules["tickets"]["export"] = "none"
    role.save()
    assert (
        user_client.get("/api/cases/analytics/export/?metric=created").status_code
        == 403
    )


def test_admin_can_create_edit_assign_role_and_invalid_id_is_rejected(
    admin_client, user_client, regular_user, org_a
):
    member = Profile.objects.get(org=org_a, user=regular_user)
    result = admin_client.post(
        "/api/roles/",
        {"name": "Sales specialist", "rules": default_rules()},
        format="json",
    )
    assert result.status_code == 201, result.data
    role_id = result.data["id"]
    rules = default_rules()
    rules["contacts"]["export"] = "none"
    result = admin_client.patch(
        f"/api/roles/{role_id}/",
        {"name": "Sales specialist", "rules": rules},
        format="json",
    )
    assert result.status_code == 200, result.data
    assert (
        admin_client.post(
            f"/api/roles/members/{member.pk}/", {"role_id": role_id}, format="json"
        ).status_code
        == 200
    )
    member.refresh_from_db()
    assert str(member.access_role_id) == role_id
    assert (
        admin_client.post(
            f"/api/roles/members/{member.pk}/", {"role_id": "invalid"}, format="json"
        ).status_code
        == 400
    )


def test_nested_company_cannot_bypass_its_own_module_scope(
    user_client, regular_user, org_a
):
    from accounts.models import Account
    from opportunity.models import Opportunity

    member = Profile.objects.get(org=org_a, user=regular_user)
    role = assign(member)
    role.rules["companies"] = {
        "view": "none",
        "create": False,
        "edit": "none",
        "delete": "none",
        "export": "none",
    }
    role.save()
    company = Account.objects.create(org=org_a, name="Private company")
    deal = Opportunity.objects.create(
        org=org_a, name="Visible deal", account=company, created_by=regular_user
    )
    deal.assigned_to.add(member)
    response = user_client.get(f"/api/opportunities/{deal.pk}/")
    assert response.status_code == 200, response.data
    assert "Private company" not in str(response.data)


def test_recommended_defaults_disable_delete_and_export():
    for scope in ("own", "team"):
        for rules in default_rules(scope).values():
            assert rules.get("delete", "none") == "none"
            assert rules["export"] == "none"


def test_creator_loses_access_after_owner_transfer(
    user_client, regular_user, org_a, admin_profile
):
    member = Profile.objects.get(org=org_a, user=regular_user)
    assign(member)
    contact = Contact.objects.create(
        org=org_a, first_name="Transferred", created_by=regular_user
    )
    contact.assigned_to.add(member)
    assert user_client.get(f"/api/contacts/{contact.pk}/").status_code == 200
    contact.assigned_to.set([admin_profile])
    assert user_client.get(f"/api/contacts/{contact.pk}/").status_code in (403, 404)
    assert not scoped(Contact.objects.all(), member).filter(pk=contact.pk).exists()


def test_member_cannot_reassign_even_owned_contact(
    user_client, regular_user, org_a, admin_profile
):
    member = Profile.objects.get(org=org_a, user=regular_user)
    assign(member)
    contact = Contact.objects.create(org=org_a, first_name="Mine")
    contact.assigned_to.add(member)
    response = user_client.patch(
        f"/api/contacts/{contact.pk}/",
        {"assigned_to": [str(admin_profile.pk)]},
        format="json",
    )
    assert response.status_code == 403
    assert list(contact.assigned_to.all()) == [member]


def test_member_create_defaults_owner_to_self(user_client, regular_user, org_a):
    from unittest.mock import patch

    member = Profile.objects.get(org=org_a, user=regular_user)
    assign(member)
    with patch("contacts.views.send_email_to_assigned_user.delay"):
        response = user_client.post(
            "/api/contacts/",
            {
                "first_name": "New member contact",
                "phone": "15551234567",
                "source": "META",
                "stage": "LEAD",
            },
            format="json",
        )
    assert response.status_code in (200, 201), response.data
    contact = Contact.objects.get(first_name="New member contact")
    assert contact.assigned_to.filter(pk=member.pk).exists()
    assert user_client.get(f"/api/contacts/{contact.pk}/").status_code == 200


def test_manager_owner_assignment_is_limited_to_team(
    user_client, regular_user, org_a, admin_profile
):
    member = Profile.objects.get(org=org_a, user=regular_user)
    assign(member, "team")
    team = Teams.objects.create(org=org_a, name="Sales")
    team.users.add(member)
    contact = Contact.objects.create(org=org_a, first_name="Team contact")
    contact.assigned_to.add(member)
    response = user_client.patch(
        f"/api/contacts/{contact.pk}/",
        {"assigned_to": [str(admin_profile.pk)]},
        format="json",
    )
    assert response.status_code == 403
    team.users.add(admin_profile)
    response = user_client.patch(
        f"/api/contacts/{contact.pk}/",
        {"assigned_to": [str(admin_profile.pk)]},
        format="json",
    )
    assert response.status_code == 200, response.data


def test_replace_contact_preserves_omitted_owner(user_client, regular_user, org_a):
    member = Profile.objects.get(org=org_a, user=regular_user)
    assign(member)
    contact = Contact.objects.create(
        org=org_a,
        first_name="Keep owner",
        phone="15551234567",
        source="META",
        stage="LEAD",
    )
    contact.assigned_to.add(member)
    response = user_client.put(
        f"/api/contacts/{contact.pk}/",
        {
            "first_name": "Still mine",
            "phone": "15551234567",
            "source": "META",
            "stage": "LEAD",
        },
        format="json",
    )
    assert response.status_code == 200, response.data
    assert contact.assigned_to.filter(pk=member.pk).exists()


@pytest.mark.parametrize("name,scope", [("Member", "own"), ("Manager", "team")])
def test_builtin_scope_cannot_be_changed(admin_client, org_a, name, scope):
    role = CRMRole.objects.create(
        org=org_a, name=name, scope=scope, rules=default_rules(scope)
    )
    response = admin_client.patch(
        f"/api/roles/{role.pk}/",
        {"name": name, "scope": "organization", "rules": default_rules("organization")},
        format="json",
    )
    assert response.status_code == 400
    role.refresh_from_db()
    assert role.scope == scope


def test_custom_permission_set_has_one_scope(admin_client):
    rules = default_rules("team")
    response = admin_client.post(
        "/api/roles/",
        {"name": "Team support", "scope": "team", "rules": rules},
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["scope"] == "team"
    rules["contacts"]["edit"] = "own"
    response = admin_client.post(
        "/api/roles/",
        {"name": "Mixed scope", "scope": "team", "rules": rules},
        format="json",
    )
    assert response.status_code == 400


def test_disabled_custom_permissions_retain_selected_scope(admin_client):
    rules = {
        module: {
            action: False if isinstance(value, bool) else "none"
            for action, value in row.items()
        }
        for module, row in default_rules().items()
    }
    response = admin_client.post(
        "/api/roles/",
        {"name": "Disabled organization set", "scope": "organization", "rules": rules},
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["scope"] == "organization"
