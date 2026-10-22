"""Owner choices and record access must agree for every active CRM object."""

import pytest
from django.apps import apps

from common.models import Profile, Teams, User
from common.rbac import ensure_default_roles
from common.testing import rls_org

pytestmark = pytest.mark.django_db
MODULES = [
    ("contacts", "contacts.contact", "contacts", "first_name"),
    ("companies", "accounts.account", "accounts", "name"),
    ("deals", "opportunity.opportunity", "opportunities", "name"),
    ("tasks", "tasks.task", "tasks", "title"),
    ("tickets", "cases.case", "cases", "name"),
]


@pytest.fixture
def audience(org_a, user_profile, admin_profile):
    member, manager = ensure_default_roles(org_a)
    user_profile.access_role = member
    user_profile.save()
    peer = Profile.objects.create(
        org=org_a,
        user=User.objects.create(email="peer@example.test"),
        access_role=member,
    )
    team = Teams.objects.create(org=org_a, name="Sales")
    team.users.add(user_profile, peer)
    other = Teams.objects.create(org=org_a, name="Other team")
    other.users.add(admin_profile)
    return peer, team, manager


@pytest.mark.parametrize(
    "module", [row[0] for row in MODULES] + ["calendar", "reports", None]
)
@pytest.mark.parametrize("role", ["member", "manager", "admin"])
def test_people_and_teams_follow_scope(
    user_client,
    admin_client,
    user_profile,
    admin_profile,
    profile_b,
    org_a,
    audience,
    module,
    role,
):
    peer, team, manager = audience
    if role == "manager":
        user_profile.access_role = manager
        user_profile.save()
    hidden = Profile.objects.create(
        org=org_a,
        user=User.objects.create(email="platform@example.test"),
        role="ADMIN",
        is_platform_access=True,
    )
    team.users.add(hidden)
    client = admin_client if role == "admin" else user_client
    response = client.get(
        "/api/users/get-teams-and-users/", {"module": module} if module else {}
    )
    assert response.status_code == 200, response.data
    expected = {str(user_profile.pk)}
    if role in ("manager", "admin"):
        expected.add(str(peer.pk))
    if role == "admin":
        expected.add(str(admin_profile.pk))
    team_count = {"member": 0, "manager": 1, "admin": 2}[role]
    if module == "reports" and role != "admin":
        # Reports are opt-in for Member and Manager roles.
        expected = set()
        team_count = 0
    assert {str(p["id"]) for p in response.data["profiles"]} == expected
    assert len(response.data["teams"]) == team_count
    assert str(profile_b.pk) not in str(response.data)
    assert str(hidden.pk) not in str(response.data)


@pytest.mark.parametrize("module,label,root,field", MODULES)
@pytest.mark.parametrize("role", ["member", "manager", "admin"])
def test_lists_filters_details_and_exports_cannot_widen_access(
    user_client,
    admin_client,
    user_profile,
    admin_profile,
    profile_b,
    org_a,
    org_b,
    audience,
    module,
    label,
    root,
    field,
    role,
):
    peer, team, manager = audience
    if role == "manager":
        user_profile.access_role = manager
        user_profile.save()
    model = apps.get_model(label)
    records = []
    for owner, title in [
        (user_profile, "OwnVisible"),
        (peer, "TeamVisible"),
        (admin_profile, "OutsideHidden"),
    ]:
        obj = model.objects.create(
            org=org_a, created_by=user_profile.user, **{field: title}
        )
        obj.assigned_to.add(owner)
        records.append(obj)
    with rls_org(org_b):
        foreign = model.objects.create(org=org_b, **{field: "TenantHidden"})
        foreign.assigned_to.add(profile_b)
    client = admin_client if role == "admin" else user_client
    visible = records[: {"member": 1, "manager": 2, "admin": 3}[role]]
    for params in (
        {},
        {"search": "Hidden"},
        {"assigned_to": str(admin_profile.pk)},
        {"board": "true"},
    ):
        response = client.get(f"/api/{root}/", params)
        assert response.status_code == 200, response.data
        for hidden in [obj for obj in records if obj not in visible] + [foreign]:
            assert str(hidden.pk) not in str(response.data)
    for obj in records + [foreign]:
        response = client.get(f"/api/{root}/{obj.pk}/")
        assert response.status_code == (200 if obj in visible else 404), response.data
    if role != "admin":
        exported = client.get(f"/api/{root}/", {"permission_action": "export"})
        assert exported.status_code == 403
        permission_set = user_profile.access_role
        permission_set.rules[module]["export"] = "team" if role == "manager" else "own"
        permission_set.save()
        exported = client.get(f"/api/{root}/", {"permission_action": "export"})
        assert exported.status_code == 200, exported.data
        for hidden in [obj for obj in records if obj not in visible] + [foreign]:
            assert str(hidden.pk) not in str(exported.data)
        reassigned = client.patch(
            f"/api/{root}/{records[0].pk}/",
            {"assigned_to": [str(admin_profile.pk)]},
            format="json",
        )
        assert reassigned.status_code == 403, reassigned.data
        assert list(records[0].assigned_to.all()) == [user_profile]
        for action, payload in [
            ("patch", {field: "Forbidden"}),
            ("patch", {"assigned_to": [str(admin_profile.pk)]}),
        ]:
            response = getattr(client, action)(
                f"/api/{root}/{records[-1].pk}/", payload, format="json"
            )
            assert response.status_code in (403, 404)


@pytest.mark.parametrize("role", ["member", "manager"])
def test_association_lookup_and_forged_id_respect_target_scope(
    user_client, user_profile, admin_profile, org_a, audience, role
):
    from accounts.models import Account
    from contacts.models import Contact

    peer, team, manager = audience
    if role == "manager":
        user_profile.access_role = manager
        user_profile.save()
    company = Account.objects.create(org=org_a, name="Own company")
    company.assigned_to.add(user_profile)
    contacts = []
    for owner in (user_profile, peer, admin_profile):
        contact = Contact.objects.create(org=org_a, first_name="Candidate")
        contact.assigned_to.add(owner)
        contacts.append(contact)
    url = f"/api/record-associations/company/{company.pk}/"
    response = user_client.get(url, {"kind": "contact", "search": "Candidate"})
    assert response.status_code == 200, response.data
    expected = contacts[: 1 if role == "member" else 2]
    assert {str(c["id"]) for c in response.data["results"]} == {
        str(c.pk) for c in expected
    }
    response = user_client.post(
        url,
        {"kind": "contact", "target": str(contacts[-1].pk), "operation": "add"},
        format="json",
    )
    assert response.status_code == 404, response.data
    assert not company.contacts.exists()


def test_disabled_module_and_invalid_picker_request(
    user_client, user_profile, audience
):
    role = user_profile.access_role
    role.rules["contacts"]["view"] = "none"
    role.save()
    response = user_client.get("/api/users/get-teams-and-users/?module=contacts")
    assert response.data == {"profiles": [], "teams": []}
    assert (
        user_client.get("/api/users/get-teams-and-users/?module=invalid").status_code
        == 400
    )
    assert (
        user_client.get(
            "/api/users/get-teams-and-users/?action=organization"
        ).status_code
        == 400
    )


@pytest.mark.parametrize("role", ["member", "manager", "admin"])
def test_search_includes_team_records_without_creator_access(
    user_client, admin_client, user_profile, admin_profile, org_a, audience, role
):
    peer, team, manager = audience
    if role == "manager":
        user_profile.access_role = manager
        user_profile.save()
    visible = set()
    for module, label, root, field in MODULES:
        if module == "tasks":  # Tasks are not offered by the global search endpoint.
            continue
        model = apps.get_model(label)
        for index, owner in enumerate((user_profile, peer, admin_profile)):
            obj = model.objects.create(
                org=org_a,
                created_by=admin_profile.user,
                **{field: f"ScopeTest {index}"},
            )
            obj.assigned_to.add(owner)
            if index < {"member": 1, "manager": 2, "admin": 3}[role]:
                visible.add(str(obj.pk))
    client = admin_client if role == "admin" else user_client
    response = client.get("/api/search/", {"q": "ScopeTest"})
    assert response.status_code == 200, response.data
    assert {r["id"] for r in response.data["results"]} == visible


@pytest.mark.parametrize("role", ["member", "manager", "admin"])
def test_report_owner_choices_exclude_unrelated_coowners(
    user_client, admin_client, user_profile, admin_profile, org_a, audience, role
):
    from contacts.models import Contact

    peer, team, manager = audience
    if role == "manager":
        user_profile.access_role = manager
        user_profile.save()
    if role != "admin":
        access_role = user_profile.access_role
        access_role.rules["reports"]["view"] = "team" if role == "manager" else "own"
        access_role.save(update_fields=["rules"])
    contact = Contact.objects.create(org=org_a, first_name="Shared")
    contact.assigned_to.add(user_profile, peer, admin_profile)
    client = admin_client if role == "admin" else user_client
    response = client.get("/api/reports/crm/", {"object": "contacts"})
    assert response.status_code == 200, response.data
    expected = (user_profile, peer, admin_profile)[
        : {"member": 1, "manager": 2, "admin": 3}[role]
    ]
    assert {p["id"] for p in response.data["owners"]} == {str(p.pk) for p in expected}
    if role != "admin":
        response = client.get(
            "/api/reports/crm/", {"object": "contacts", "owner": str(admin_profile.pk)}
        )
        assert response.status_code == 400


def test_manager_team_scope_is_not_transitive_and_excludes_inactive_profiles(
    user_client, user_profile, admin_profile, audience
):
    peer, team, manager = audience
    user_profile.access_role = manager
    user_profile.save()
    admin_profile.user_teams.first().users.add(peer)
    peer.is_active = False
    peer.save()
    response = user_client.get(
        "/api/users/get-teams-and-users/", {"module": "contacts", "action": "reassign"}
    )
    assert response.status_code == 200
    assert {p["id"] for p in response.data["profiles"]} == {str(user_profile.pk)}
    team.users.remove(user_profile)
    response = user_client.get(
        "/api/users/get-teams-and-users/", {"module": "contacts"}
    )
    assert {p["id"] for p in response.data["profiles"]} == {str(user_profile.pk)}
    assert response.data["teams"] == []


@pytest.mark.parametrize("module,label,root,field", MODULES)
@pytest.mark.parametrize("role", ["member", "manager", "admin"])
def test_creation_schema_self_assignment_for_members_only(
    user_client, admin_client, user_profile, audience, module, label, root, field, role
):
    peer, team, manager = audience
    if role == "manager":
        user_profile.access_role = manager
        user_profile.save()
    model = apps.get_model(label)
    client = admin_client if role == "admin" else user_client
    response = client.get(f"/api/creation-forms/{model.__name__}/")
    assert response.status_code == 200, response.data
    if role == "member":
        assert response.data["assignment"]["mode"] == "self"
        assert response.data["assignment"]["id"] == str(user_profile.pk)
    else:
        assert "assignment" not in response.data


@pytest.mark.parametrize("module,label,root,field", MODULES)
def test_member_creation_without_owner_assigns_self_and_edit_preserves_it(
    user_client, user_profile, org_a, audience, module, label, root, field
):
    model = apps.get_model(label)
    key = "name" if module == "contacts" else field
    response = user_client.post(
        f"/api/{root}/", {key: "Automatic owner"}, format="json"
    )
    assert response.status_code in (200, 201), response.data
    record = model.objects.get(org=org_a, **{field: "Automatic owner"})
    assert list(record.assigned_to.all()) == [user_profile]
    response = user_client.patch(
        f"/api/{root}/{record.pk}/", {key: "Updated title"}, format="json"
    )
    assert response.status_code == 200, response.data
    assert list(record.assigned_to.all()) == [user_profile]
