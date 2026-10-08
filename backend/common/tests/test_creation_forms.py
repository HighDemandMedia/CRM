"""Org creation layouts must not weaken domain validation or tenant boundaries."""

import pytest
from rest_framework.exceptions import ValidationError

from common.creation_forms import (
    configuration,
    validate_configuration,
    validate_creation,
)
from common.models import CRMRole, CustomFieldDefinition
from common.property_catalog import target_model
from common.rbac import default_rules

pytestmark = pytest.mark.django_db
URL = "/api/creation-forms/"
OBJECTS = [
    ("Contact", "contacts", "name"),
    ("Account", "accounts", "name"),
    ("Opportunity", "opportunities", "name"),
    ("Task", "tasks", "title"),
    ("Case", "cases", "name"),
]


def save(client, target, fields):
    current = client.get(URL, {"target_model": target}).data
    return client.put(
        URL,
        {"target_model": target, "revision": current["revision"], "selected": fields},
        format="json",
    )


def row(key, required=False):
    return {"key": key, "required": required}


@pytest.mark.parametrize("target,endpoint,key", OBJECTS)
def test_catalog_defaults_and_manual_creation(
    admin_client, org_a, target, endpoint, key
):
    config = admin_client.get(URL, {"target_model": target})
    assert config.status_code == 200, config.data
    assert config.data["selected"][0]["locked"]
    assert not any(
        f["key"] in {"id", "created_at", "appointment_at"}
        for f in config.data["fields"]
    )
    CustomFieldDefinition.objects.create(
        org=org_a,
        target_model=target,
        key="reference",
        label="Reference",
        field_type="text",
    )
    identity = "first_name" if target == "Contact" else key
    assert (
        save(
            admin_client,
            target,
            [row(identity, True), row("custom_fields.reference", True)],
        ).status_code
        == 200
    )
    response = admin_client.post(
        f"/api/{endpoint}/", {key: "Creation form regression"}, format="json"
    )
    assert response.status_code == 400, response.data
    assert "custom_fields.reference" in response.data
    payload = {key: "Creation form regression", "custom_fields": {"reference": "A-123"}}
    if target == "Task":
        payload.update(status="New", priority="Medium")
    response = admin_client.post(f"/api/{endpoint}/", payload, format="json")
    assert response.status_code in (200, 201), response.data
    record = target_model(target).objects.get(
        org=org_a, custom_fields__reference="A-123"
    )
    # Creation-only requirements never force legacy/edit forms to resubmit them.
    response = admin_client.patch(
        f"/api/{endpoint}/{record.pk}/", {key: "Renamed"}, format="json"
    )
    assert response.status_code == 200, response.data


def test_permissions_and_org_isolation(
    admin_client, user_client, user_profile, org_b_client, org_a
):
    assert user_client.get(URL).status_code == 403
    assert user_client.get(URL + "Contact/").status_code == 200
    assert user_client.put(URL, {}, format="json").status_code == 403
    manager = CRMRole.objects.create(
        org=org_a,
        name="Manager",
        scope="team",
        rules=default_rules("team"),
        settings_access={"creation_forms": "read"},
    )
    user_profile.access_role = manager
    user_profile.save()
    assert user_client.get(URL).status_code == 200
    assert user_client.put(URL, {}, format="json").status_code == 403
    manager.settings_access = {"creation_forms": "manage"}
    manager.save()
    assert (
        save(
            user_client, "Contact", [row("first_name", True), row("phone", True)]
        ).status_code
        == 200
    )
    assert [f["key"] for f in admin_client.get(URL + "Contact/").data["selected"]] == [
        "first_name",
        "phone",
    ]
    assert len(org_b_client.get(URL + "Contact/").data["selected"]) > 2


def test_order_revision_and_invalid_configuration(admin_client, org_a):
    before = admin_client.get(URL).data
    rows = [row("email"), row("first_name", True)]
    result = save(admin_client, "Contact", rows)
    assert [f["key"] for f in result.data["selected"]] == ["email", "first_name"]
    assert (
        admin_client.put(
            URL,
            {
                "target_model": "Contact",
                "revision": before["revision"],
                "selected": rows,
            },
            format="json",
        ).status_code
        == 409
    )
    for invalid in [
        [],
        [row("first_name")],
        [row("first_name", True), row("first_name")],
        [row("first_name", True), row("id")],
        [row("first_name", True), row("email", "true")],
    ]:
        assert save(admin_client, "Contact", invalid).status_code == 400
    assert admin_client.put(URL, {"target_model": {}}, format="json").status_code == 400
    with pytest.raises(ValidationError):
        validate_configuration(
            org_a, "Task", [row("title", True), row("account", True), row("case", True)]
        )
    with pytest.raises(ValidationError):
        validate_configuration(
            org_a, "Task", [row("title", True), row("reminder_days", True)]
        )


def test_property_opt_in_and_definition_changes(admin_client, org_a):
    for key, include in [("unused", False), ("included", True)]:
        response = admin_client.post(
            "/api/custom-fields/",
            {
                "target_model": "Contact",
                "key": key,
                "label": key,
                "field_type": "text",
                "add_to_creation_form": include,
            },
            format="json",
        )
        assert response.status_code == 201, response.data
    selected = admin_client.get(URL + "Contact/").data["selected"]
    assert "custom_fields.unused" not in [f["key"] for f in selected]
    assert "custom_fields.included" in [f["key"] for f in selected]
    definition = CustomFieldDefinition.objects.get(org=org_a, key="included")
    definition.label = "Updated label"
    definition.save()
    assert (
        admin_client.get(URL + "Contact/").data["selected"][-1]["label"]
        == "Updated label"
    )
    definition.is_active = False
    definition.save()
    assert "custom_fields.included" not in [
        f["key"] for f in admin_client.get(URL + "Contact/").data["selected"]
    ]


def test_opt_in_requires_both_permissions(user_client, user_profile, org_a):
    role = CRMRole.objects.create(
        org=org_a,
        name="Manager",
        scope="team",
        rules=default_rules("team"),
        settings_access={"properties": "manage"},
    )
    user_profile.access_role = role
    user_profile.save()
    response = user_client.post(
        "/api/custom-fields/",
        {
            "target_model": "Contact",
            "key": "denied",
            "label": "Denied",
            "field_type": "text",
            "add_to_creation_form": True,
        },
        format="json",
    )
    assert response.status_code == 403
    assert not CustomFieldDefinition.objects.filter(org=org_a, key="denied").exists()


def test_required_values_keep_zero_and_false(org_a):
    for key, kind in [("quantity", "number"), ("approved", "checkbox")]:
        CustomFieldDefinition.objects.create(
            org=org_a, target_model="Contact", key=key, label=key, field_type=kind
        )
    org_a.creation_forms = {
        "Contact": [
            row("first_name", True),
            row("custom_fields.quantity", True),
            row("custom_fields.approved", True),
        ]
    }
    validate_creation(
        org_a,
        "Contact",
        {"name": "A", "custom_fields": {"quantity": 0, "approved": False}},
    )
    for value in ["", " ", None, [], {}]:
        with pytest.raises(ValidationError):
            validate_creation(
                org_a,
                "Contact",
                {"name": "A", "custom_fields": {"quantity": value, "approved": False}},
            )


@pytest.mark.parametrize("target,endpoint,key", OBJECTS)
def test_default_form_with_optional_blanks(admin_client, org_a, target, endpoint, key):
    fields = configuration(org_a, target)["selected"]
    payload = {}
    defaults = {
        "stage": "PROSPECTING" if target == "Opportunity" else "LEAD",
        "status": "New",
        "priority": "Normal"
        if target == "Case"
        else "Medium"
        if target == "Task"
        else None,
        "category": "General",
        "source": "Internal" if target == "Case" else None,
        "currency": "USD",
    }
    for f in fields:
        name = "name" if f["key"] == "first_name" else f["key"]
        if f["relation"] and not f["multiple"] and name != "assigned_to":
            continue
        value = defaults.get(name, [] if f["multiple"] or name == "pages" else None)
        if name == "assigned_to":
            value = []
        if target == "Task" and name in {"description", "priority"} and value is None:
            value = ""
        if name in {"waiting_reason", "resolution_note"}:
            value = ""
        payload["tag_ids" if target == "Account" and name == "tags" else name] = value
    payload[key] = "Default form test"
    response = admin_client.post(f"/api/{endpoint}/", payload, format="json")
    assert response.status_code in (200, 201), response.data
