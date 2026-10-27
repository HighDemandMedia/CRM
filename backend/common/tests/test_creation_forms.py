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


def identifiers(target):
    return (
        {"email": "identity@example.com", "phone": "+13055550199"}
        if target == "Contact"
        else {"website": "https://example.com"}
        if target == "Account"
        else {}
    )


def row(key, required=False):
    return {"key": key, "required": required}


@pytest.mark.parametrize("target,endpoint,key", OBJECTS)
def test_catalog_defaults_and_manual_creation(
    admin_client, admin_profile, org_a, target, endpoint, key
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
            [row(identity, True), row("custom_fields.reference", True)]
            + [row(key, True) for key in identifiers(target)]
            + ([row("assigned_to", True)] if target in {"Task", "Case"} else []),
        ).status_code
        == 200
    )
    assignment = (
        {"assigned_to": [str(admin_profile.pk)]} if target in {"Task", "Case"} else {}
    )
    response = admin_client.post(
        f"/api/{endpoint}/",
        {key: "Creation form regression", **assignment, **identifiers(target)},
        format="json",
    )
    assert response.status_code == 400, response.data
    assert "custom_fields.reference" in response.data
    payload = {
        key: "Creation form regression",
        "custom_fields": {"reference": "A-123"},
        **assignment,
        **identifiers(target),
    }
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
            user_client,
            "Contact",
            [row("first_name", True), row("phone", True), row("email", True)],
        ).status_code
        == 200
    )
    assert [f["key"] for f in admin_client.get(URL + "Contact/").data["selected"]] == [
        "first_name",
        "phone",
        "email",
    ]
    assert len(org_b_client.get(URL + "Contact/").data["selected"]) > 2


def test_order_revision_and_invalid_configuration(admin_client, org_a):
    before = admin_client.get(URL).data
    rows = [row("email", True), row("first_name", True), row("phone", True)]
    result = save(admin_client, "Contact", rows)
    assert [f["key"] for f in result.data["selected"]] == [
        "email",
        "first_name",
        "phone",
    ]
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
        {
            "name": "A",
            **identifiers("Contact"),
            "custom_fields": {"quantity": 0, "approved": False},
        },
    )
    for value in ["", " ", None, [], {}]:
        with pytest.raises(ValidationError):
            validate_creation(
                org_a,
                "Contact",
                {
                    "name": "A",
                    **identifiers("Contact"),
                    "custom_fields": {"quantity": value, "approved": False},
                },
            )


@pytest.mark.parametrize("target,endpoint,key", OBJECTS)
def test_default_form_with_optional_blanks(
    admin_client, admin_profile, org_a, target, endpoint, key
):
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
            value = [str(admin_profile.pk)] if target in {"Task", "Case"} else []
        if target == "Task" and name in {"description", "priority"} and value is None:
            value = ""
        if name in {"waiting_reason", "resolution_note"}:
            value = ""
        payload["tag_ids" if target == "Account" and name == "tags" else name] = value
    payload.update(identifiers(target))
    payload[key] = "Default form test"
    response = admin_client.post(f"/api/{endpoint}/", payload, format="json")
    assert response.status_code in (200, 201), response.data


@pytest.mark.parametrize("target", ["Contact", "Account", "Opportunity"])
def test_default_address_order_and_saved_order(org_a, target):
    defaults = configuration(org_a, target)
    keys = [field["key"] for field in defaults["selected"]]
    assert keys.index("state") + 1 == keys.index("address_line")
    identity = "first_name" if target == "Contact" else "name"
    org_a.creation_forms = {
        target: [row(identity, True), row("address_line"), row("city"), row("state")]
    }
    saved = configuration(org_a, target)
    assert [field["key"] for field in saved["selected"]] == [
        identity,
        *(
            ["phone", "email"]
            if target == "Contact"
            else ["website"]
            if target == "Account"
            else []
        ),
        "address_line",
        "city",
        "state",
    ]


@pytest.mark.parametrize("required", [{"email"}, {"phone"}, {"email", "phone"}])
def test_admin_configures_contact_identifiers(admin_client, org_a, required):
    layout = [row("first_name", True)] + [
        row(k, k in required) for k in ("email", "phone")
    ]
    response = save(admin_client, "Contact", layout)
    assert response.status_code == 200, response.data
    config = admin_client.get(URL, {"target_model": "Contact"}).data
    identifiers = {
        f["key"]: f for f in config["selected"] if f["key"] in {"email", "phone"}
    }
    assert {key for key, f in identifiers.items() if f["required"]} == required
    assert not any(f["locked"] for f in identifiers.values())
    payload = {
        "name": "Configured identity",
        **{
            key: value
            for key, value in {
                "email": "configured@example.com",
                "phone": "+12025550123",
            }.items()
            if key in required
        },
    }
    created = admin_client.post("/api/contacts/", payload, format="json")
    assert created.status_code == 200, created.data
    org_a.refresh_from_db()
    validate_creation(org_a, "Contact", payload)
    for key in required:
        invalid = {k: v for k, v in payload.items() if k != key}
        result = admin_client.post("/api/contacts/", invalid, format="json")
        assert result.status_code == 400
        assert key in result.data or key in result.data.get("errors", {})


def test_admin_cannot_make_both_contact_identifiers_optional(admin_client):
    result = save(
        admin_client, "Contact", [row("first_name", True), row("email"), row("phone")]
    )
    assert result.status_code == 400
    assert "email or phone" in str(result.data)


@pytest.mark.parametrize("existing_key", ["email", "phone"])
def test_legacy_contact_cannot_clear_last_identifier(
    org_a, admin_profile, existing_key
):
    from types import SimpleNamespace

    from contacts.models import Contact
    from contacts.serializer import CreateContactSerializer

    required_key = "phone" if existing_key == "email" else "email"
    org_a.creation_forms = {
        "Contact": [row("first_name", True), row(required_key, True)]
    }
    contact = Contact.objects.create(
        org=org_a,
        first_name="Legacy",
        **{
            existing_key: "legacy@example.com"
            if existing_key == "email"
            else "+12025550123"
        },
    )
    request = SimpleNamespace(profile=admin_profile)
    for data, valid in [
        ({"name": "Updated legacy"}, True),
        ({existing_key: ""}, False),
    ]:
        serializer = CreateContactSerializer(
            contact, data=data, partial=True, request_obj=request
        )
        assert serializer.is_valid() is valid, serializer.errors
        if not valid:
            assert "Provide an email address or phone number." in str(serializer.errors)


@pytest.mark.parametrize("required", ["email", "phone"])
def test_optional_identifier_still_checks_duplicates(admin_client, org_a, required):
    from contacts.models import Contact

    save(admin_client, "Contact", [row("first_name", True), row(required, True)])
    Contact.objects.create(
        org=org_a,
        first_name="Original",
        email="original@example.com",
        phone="+12025550123",
    )
    optional = "phone" if required == "email" else "email"
    payload = {
        "name": "Duplicate",
        "email": "original@example.com"
        if optional == "email"
        else "different@example.com",
        "phone": "+12025550123" if optional == "phone" else "+12025550124",
    }
    response = admin_client.post("/api/contacts/", payload, format="json")
    assert response.status_code == 400
    assert optional in response.data["errors"]
