"""The same creation policy applies to tasks and tickets, including direct API calls."""

import pytest
from rest_framework.exceptions import ValidationError

from accounts.models import Account
from common.creation_forms import (
    configuration,
    validate_configuration,
    validate_creation,
)
from common.models import CRMRole
from common.property_catalog import target_model
from common.rbac import default_rules
from common.testing import rls_org
from contacts.models import Contact

pytestmark = pytest.mark.django_db


@pytest.fixture(params=[("Task", "tasks", "title"), ("Case", "cases", "name")])
def work_item(request):
    return request.param


def payload(work_item, **extra):
    return {work_item[2]: "Creation policy test", "status": "New", **extra}


def post(client, work_item, **extra):
    return client.post(
        f"/api/{work_item[1]}/", payload(work_item, **extra), format="json"
    )


def test_admin_must_choose_active_org_assignee(
    admin_client, admin_profile, profile_b, work_item
):
    model = target_model(work_item[0])
    before = model.objects.count()
    for owners in (None, [], [str(profile_b.pk)]):
        response = post(admin_client, work_item, assigned_to=owners)
        assert response.status_code == 400, response.data
        assert "assigned_to" in response.data
    assert model.objects.count() == before
    admin_profile.is_active = False
    admin_profile.save()
    # The disabled session itself is rejected before the create handler.
    assert (
        post(admin_client, work_item, assigned_to=[str(admin_profile.pk)]).status_code
        == 403
    )


def test_manager_must_choose_and_respects_assignment_scope(
    user_client, user_profile, admin_profile, org_a, work_item
):
    user_profile.access_role = CRMRole.objects.create(
        org=org_a, name="Manager", scope="team", rules=default_rules("team")
    )
    user_profile.save()
    for owners in (None, []):
        response = post(user_client, work_item, assigned_to=owners)
        assert response.status_code == 400, response.data
    assert (
        post(user_client, work_item, assigned_to=[str(admin_profile.pk)]).status_code
        == 403
    )
    response = post(user_client, work_item, assigned_to=[str(user_profile.pk)])
    assert response.status_code in (200, 201), response.data


@pytest.mark.parametrize("configured", [False, True])
def test_member_is_self_assigned(
    user_client, user_profile, admin_profile, org_a, work_item, configured
):
    if configured:
        user_profile.access_role = CRMRole.objects.create(
            org=org_a, name="Member", scope="own", rules=default_rules("own")
        )
        user_profile.save()
    response = post(user_client, work_item)
    assert response.status_code in (200, 201), response.data
    record = target_model(work_item[0]).objects.get(org=org_a)
    assert list(record.assigned_to.all()) == [user_profile]
    assert post(
        user_client, work_item, assigned_to=[str(admin_profile.pk)]
    ).status_code in (400, 403)
    schema = user_client.get(f"/api/creation-forms/{work_item[0]}/").data
    assert schema["assignment"] == {
        "mode": "self",
        "id": str(user_profile.pk),
        "name": user_profile.user.display_name,
    }


@pytest.mark.parametrize("kind", ["account", "contacts", "both"])
def test_associate_company_contacts_or_both(
    admin_client, admin_profile, org_a, work_item, kind
):
    account = Account.objects.create(org=org_a, name="Company")
    contact = Contact.objects.create(org=org_a, first_name="Contact")
    associations = {}
    if kind in {"account", "both"}:
        associations["account"] = str(account.pk)
    if kind in {"contacts", "both"}:
        associations["contacts"] = [str(contact.pk)]
    response = post(
        admin_client, work_item, assigned_to=[str(admin_profile.pk)], **associations
    )
    assert response.status_code in (200, 201), response.data
    record = target_model(work_item[0]).objects.get(org=org_a)
    assert record.account_id == (account.pk if kind != "contacts" else None)
    assert list(record.contacts.all()) == ([contact] if kind != "account" else [])


@pytest.mark.parametrize("key", ["account", "contacts"])
def test_cross_org_associations_rejected(
    admin_client, admin_profile, org_b, work_item, key
):
    with rls_org(org_b):
        record = (
            Account.objects.create(org=org_b, name="Other")
            if key == "account"
            else Contact.objects.create(org=org_b, first_name="Other")
        )
    value = str(record.pk) if key == "account" else [str(record.pk)]
    response = post(
        admin_client, work_item, assigned_to=[str(admin_profile.pk)], **{key: value}
    )
    assert response.status_code == 400, response.data
    assert key in response.data.get("errors", response.data)
    assert not target_model(work_item[0]).objects.exists()


def test_legacy_layout_normalizes_and_required_associations(work_item, org_a):
    target, _, identity = work_item
    org_a.creation_forms = {
        target: [
            {"key": identity, "required": True},
            {"key": "contacts", "required": True},
            {"key": "account", "required": False},
        ]
    }
    schema = configuration(org_a, target)
    assert [f["key"] for f in schema["selected"]] == [
        identity,
        "assigned_to",
        "associations",
    ]
    assert not {"account", "contacts", "opportunity", "case"} & {
        f["key"] for f in schema["fields"]
    }
    rows = [{"key": f["key"], "required": f["required"]} for f in schema["selected"]]
    assert validate_configuration(org_a, target, rows) == rows
    for invalid in (
        rows[:1],
        [dict(r, required=False) if r["key"] == "assigned_to" else r for r in rows],
    ):
        with pytest.raises(ValidationError):
            validate_configuration(org_a, target, invalid)
    with pytest.raises(ValidationError):
        validate_creation(
            org_a, target, payload(work_item, assigned_to=["self"], contacts="[]")
        )
    for links in (
        {"account": "company"},
        {"contacts": ["75eec16e-a0bb-4f2c-a8df-b922b17a0c1c"]},
    ):
        validate_creation(
            org_a, target, payload(work_item, assigned_to=["self"], **links)
        )


def test_inactive_assignee_rejected(admin_client, user_profile, work_item):
    user_profile.is_active = False
    user_profile.save()
    response = post(admin_client, work_item, assigned_to=[str(user_profile.pk)])
    assert response.status_code == 400
    assert "assigned_to" in response.data


def test_multiple_assignees_preserved_in_multipart(
    admin_client, admin_profile, user_profile, org_a, work_item
):
    import json

    response = admin_client.post(
        f"/api/{work_item[1]}/",
        payload(
            work_item,
            assigned_to=json.dumps([str(admin_profile.pk), str(user_profile.pk)]),
        ),
        format="multipart",
    )
    assert response.status_code in (200, 201), response.data
    record = target_model(work_item[0]).objects.get(org=org_a)
    assert set(record.assigned_to.all()) == {admin_profile, user_profile}


def test_member_cannot_link_inaccessible_contact(
    user_client, user_profile, admin_profile, org_a, work_item
):
    user_profile.access_role = CRMRole.objects.create(
        org=org_a, name="Member", scope="own", rules=default_rules("own")
    )
    user_profile.save()
    contact = Contact.objects.create(org=org_a, first_name="Private")
    contact.assigned_to.add(admin_profile)
    response = post(user_client, work_item, contacts=[str(contact.pk)])
    assert response.status_code == 400, response.data
    assert "contacts" in response.data
    assert not target_model(work_item[0]).objects.exists()
