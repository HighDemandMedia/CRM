from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from common.models import CRMRole, SalesAppointment, Teams
from common.rbac import (
    calendar_scoped,
    default_rules,
    validate_record_fields,
    validate_rules,
)
from common.testing import rls_org
from contacts.models import Contact

pytestmark = pytest.mark.django_db


def set_role(profile, scope="own", **changes):
    rules = default_rules(scope)
    for module, actions in changes.items():
        rules[module].update(actions)
    role = CRMRole.objects.create(
        org=profile.org, name="Permission test", scope=scope, rules=rules
    )
    profile.access_role = role
    profile.save()
    return role


def event(org, host, title="Private event"):
    start = timezone.now() + timedelta(days=1)
    return SalesAppointment.objects.create(
        org=org,
        host=host,
        title=title,
        starts_at=start,
        ends_at=start + timedelta(hours=1),
        created_by=host.user,
    )


def booking(host, **changes):
    start = timezone.now() + timedelta(days=2)
    return {
        "title": "Permission test",
        "host": str(host.pk),
        "starts_at": start.isoformat(),
        "ends_at": (start + timedelta(hours=1)).isoformat(),
        **changes,
    }


def test_catalog_and_non_admin_management(admin_client, user_client, user_profile):
    set_role(user_profile)
    response = admin_client.get("/api/roles/")
    assert response.status_code == 200
    assert {m["key"] for m in response.data["catalog"]} == {
        "contacts",
        "companies",
        "deals",
        "tasks",
        "tickets",
        "calendar",
        "reports",
    }
    assert user_client.get("/api/roles/").status_code == 403
    data = user_client.get("/api/permissions/me/").data
    assert data["rules"]["calendar"]["cancel"] == "none"
    assert data["calendar_host_ids"] == [user_profile.pk]


@pytest.mark.parametrize(
    "action,payload",
    [("stage", {"stage": "QUALIFIED"}), ("notes", {"description": "New note"})],
)
def test_specific_actions_cannot_bypass_via_standard_edit(
    user_client, user_profile, org_a, action, payload
):
    set_role(user_profile, contacts={action: "none"})
    contact = Contact.objects.create(org=org_a, first_name="Test", stage="LEAD")
    contact.assigned_to.add(user_profile)
    response = user_client.patch(f"/api/contacts/{contact.pk}/", payload, format="json")
    assert response.status_code == 403, response.data
    assert (
        user_client.patch(
            f"/api/contacts/{contact.pk}/", {"first_name": "Allowed"}, format="json"
        ).status_code
        == 200
    )


def test_note_create_without_permission_is_denied(user_client, user_profile, org_a):
    set_role(user_profile, contacts={"notes": "none"})
    contact = Contact.objects.create(org=org_a, first_name="Test")
    contact.assigned_to.add(user_profile)
    assert (
        user_client.post(
            f"/api/contacts/{contact.pk}/", {"comment": "Blocked"}, format="json"
        ).status_code
        == 403
    )


def test_unchanged_optional_fields_do_not_block_edit(user_profile, org_a):
    set_role(
        user_profile,
        contacts={"stage": "none", "notes": "none", "associations": "none"},
    )
    contact = Contact.objects.create(
        org=org_a, first_name="Test", stage="LEAD", description="Existing"
    )
    contact.assigned_to.add(user_profile)
    request = SimpleNamespace(
        profile=user_profile,
        data={"stage": "LEAD", "description": "Existing", "account": None},
        path="/api/contacts/",
        FILES={},
    )
    validate_record_fields(request, "contacts", contact)


def test_permission_dependencies_rejected():
    rules = default_rules()
    rules["contacts"]["edit"] = "none"
    with pytest.raises(ValidationError):
        validate_rules(rules)
    rules = default_rules()
    rules["calendar"]["view"] = "none"
    with pytest.raises(ValidationError):
        validate_rules(rules)


def test_read_only_report_does_not_allow_csv(user_client, user_profile, org_a):
    set_role(user_profile)
    response = user_client.get("/api/reports/crm/?object=contacts")
    assert response.status_code == 200, response.data
    assert (
        user_client.get("/api/reports/crm/?object=contacts&download=csv").status_code
        == 403
    )


def test_reports_module_and_object_both_required(user_client, user_profile):
    role = set_role(user_profile, reports={"view": "none"})
    assert user_client.get("/api/reports/crm/").status_code == 403
    role.rules = default_rules()
    role.rules["reports"]["export"] = "own"
    role.save()
    assert (
        user_client.get("/api/reports/crm/?object=contacts&download=csv").status_code
        == 403
    )
    role.rules["contacts"]["export"] = "own"
    role.save()
    assert (
        user_client.get("/api/reports/crm/?object=contacts&download=csv").status_code
        == 200
    )


def test_no_report_objects_is_forbidden_not_server_error(user_client, user_profile):
    rules = default_rules()
    for key in ("contacts", "companies", "deals", "tasks", "tickets", "calendar"):
        rules[key]["view"] = "none"
    role = set_role(user_profile)
    role.rules = rules
    role.save()
    assert user_client.get("/api/reports/crm/").status_code == 403


def test_calendar_own_team_org_visibility(
    user_profile, admin_profile, profile_b, org_a, org_b
):
    role = set_role(user_profile)
    mine = event(org_a, user_profile)
    theirs = event(org_a, admin_profile)
    with rls_org(org_b):
        other = event(org_b, profile_b)
    assert set(
        calendar_scoped(SalesAppointment.objects.all(), user_profile).values_list(
            "pk", flat=True
        )
    ) == {mine.pk}
    team = Teams.objects.create(org=org_a, name="Test team")
    team.users.add(user_profile, admin_profile)
    role.rules = default_rules("team")
    role.scope = "team"
    role.save()
    user_profile.refresh_from_db()
    assert set(
        calendar_scoped(SalesAppointment.objects.all(), user_profile).values_list(
            "pk", flat=True
        )
    ) == {mine.pk, theirs.pk}
    assert (
        not calendar_scoped(SalesAppointment.objects.all(), user_profile)
        .filter(pk=other.pk)
        .exists()
    )


def test_attendee_can_view_but_not_reschedule(
    user_client, user_profile, admin_profile, org_a
):
    set_role(user_profile)
    meeting = event(org_a, admin_profile)
    meeting.attendee_users.add(user_profile)
    assert (
        calendar_scoped(SalesAppointment.objects.all(), user_profile)
        .filter(pk=meeting.pk)
        .exists()
    )
    assert (
        user_client.patch(
            f"/api/sales-appointments/{meeting.pk}/",
            {"operation": "reschedule"},
            format="json",
        ).status_code
        == 404
    )


def test_calendar_create_cancel_and_delegate_are_separate(
    user_client, user_profile, admin_profile, org_a
):
    role = set_role(user_profile)
    assert (
        user_client.post(
            "/api/sales-appointments/", booking(admin_profile), format="json"
        ).status_code
        == 400
    )
    response = user_client.post(
        "/api/sales-appointments/", booking(user_profile), format="json"
    )
    assert response.status_code == 201, response.data
    url = f"/api/sales-appointments/{response.data['id']}/"
    assert (
        user_client.patch(url, {"operation": "cancel"}, format="json").status_code
        == 403
    )
    role.rules["calendar"]["cancel"] = "own"
    role.save()
    assert (
        user_client.patch(url, {"operation": "cancel"}, format="json").status_code
        == 200
    )


def test_conflict_override_is_not_implied_by_create(user_client, user_profile):
    role = set_role(user_profile)
    body = booking(user_profile)
    assert (
        user_client.post("/api/sales-appointments/", body, format="json").status_code
        == 201
    )
    assert (
        user_client.post(
            "/api/sales-appointments/", {**body, "allow_overlap": True}, format="json"
        ).status_code
        == 403
    )
    role.rules["calendar"]["override_conflicts"] = True
    role.save()
    assert (
        user_client.post(
            "/api/sales-appointments/", {**body, "allow_overlap": True}, format="json"
        ).status_code
        == 201
    )


def test_calendar_does_not_leak_attendee_without_contact_access(
    user_client, user_profile, admin_profile, org_a
):
    set_role(user_profile)
    private = Contact.objects.create(
        org=org_a, first_name="Secret", email="private@example.com"
    )
    private.assigned_to.add(admin_profile)
    meeting = event(org_a, user_profile)
    meeting.contact = private
    meeting.save()
    meeting.contacts.add(private)
    response = user_client.get(
        "/api/sales-appointments/",
        {"start": meeting.starts_at.isoformat(), "end": meeting.ends_at.isoformat()},
    )
    assert response.status_code == 200, response.data
    assert "private@example.com" not in str(response.data)
    assert response.data[0]["attendee"] is None


@pytest.mark.parametrize(
    "url",
    [
        "/api/contacts/import/preview/",
        "/api/cases/bulk/delete/",
        "/api/contacts/00000000-0000-0000-0000-000000000001/merge/",
    ],
)
def test_sensitive_operations_stay_admin_only(user_client, user_profile, url):
    set_role(user_profile)
    assert user_client.post(url, {}, format="json").status_code == 403


def test_role_edits_are_audited_with_before_and_after(admin_client, admin_user, org_a):
    from common.audit_log import SecurityAuditLog

    rules = default_rules()
    response = admin_client.post(
        "/api/roles/",
        {"name": "Audited set", "scope": "own", "rules": rules},
        format="json",
    )
    assert response.status_code == 201, response.data
    role_id = response.data["id"]
    rules["calendar"]["cancel"] = "own"
    response = admin_client.patch(
        f"/api/roles/{role_id}/",
        {"name": "Audited set", "scope": "own", "rules": rules},
        format="json",
    )
    assert response.status_code == 200, response.data
    entry = SecurityAuditLog.objects.filter(
        event_type="PERMISSION_SET_CHANGED",
        org=org_a,
        description="Permission set updated",
    ).first()
    assert entry.user_id == admin_user.pk
    assert entry.metadata["before"]["rules"]["calendar"]["cancel"] == "none"
    assert entry.metadata["after"]["rules"]["calendar"]["cancel"] == "own"


def test_migration_preserves_custom_permissions_and_denies_new_tools(
    user_profile, org_a
):
    import importlib

    from django.apps import apps
    from django.db import connection

    rules = {
        key: row
        for key, row in default_rules().items()
        if key not in ("calendar", "reports")
    }
    for row in rules.values():
        for action in ("stage", "notes", "attachments", "associations"):
            row.pop(action)
    rules["contacts"]["export"] = "own"
    role = CRMRole.objects.create(
        org=org_a, name="Legacy custom", scope="own", rules=rules
    )
    migration = importlib.import_module(
        "common.migrations.0064_expanded_crm_permissions"
    )
    migration.expand(apps, SimpleNamespace(connection=connection))
    role.refresh_from_db()
    user_profile.refresh_from_db()
    assert role.rules["contacts"]["export"] == "own"
    assert role.rules["contacts"]["notes"] == "own"
    assert role.rules["calendar"]["view"] == "none"
    assert role.rules["reports"]["view"] == "none"
    assert user_profile.access_role.name == "Member"


def test_activity_feed_does_not_reveal_inaccessible_record(
    user_client, user_profile, admin_profile, org_a
):
    from common.models import Activity

    set_role(user_profile)
    own = Contact.objects.create(org=org_a, first_name="Mine")
    own.assigned_to.add(user_profile)
    private = Contact.objects.create(org=org_a, first_name="Secret")
    private.assigned_to.add(admin_profile)
    for record in (own, private):
        Activity.objects.create(
            org=org_a,
            user=admin_profile,
            entity_type="Contact",
            entity_id=record.pk,
            entity_name=record.first_name,
            action="UPDATE",
            description=record.first_name,
        )
    response = user_client.get("/api/activities/")
    assert response.status_code == 200, response.data
    assert "Secret" not in str(response.data)
    assert "Mine" in str(response.data)
