from unittest.mock import patch
from uuid import uuid4

import pytest
from django.apps import apps

from accounts.models import Account
from common.models import CustomFieldDefinition
from common.testing import rls_org
from contacts.models import Contact

pytestmark = pytest.mark.django_db


def endpoint(field):
    return f"/api/custom-fields/{field.pk}/?permanent=true"


@pytest.fixture
def field(org_a):
    return CustomFieldDefinition.objects.create(
        org=org_a,
        target_model="Contact",
        key="custom_rating",
        label="Rating",
        field_type="number",
    )


def test_delete_requires_admin_and_typed_confirmation(
    admin_client, user_client, field, org_a
):
    contact = Contact.objects.create(
        org=org_a, first_name="Keep", custom_fields={field.key: 0}
    )
    assert (
        user_client.delete(
            endpoint(field), {"confirmation": field.key}, format="json"
        ).status_code
        == 403
    )
    for confirmation in ("", "Rating", "wrong"):
        assert (
            admin_client.delete(
                endpoint(field), {"confirmation": confirmation}, format="json"
            ).status_code
            == 400
        )
    contact.refresh_from_db()
    assert contact.custom_fields == {field.key: 0}
    assert CustomFieldDefinition.objects.filter(pk=field.pk).exists()


@pytest.mark.parametrize(
    "target,app,name_key",
    [
        ("Contact", "contacts", "first_name"),
        ("Account", "accounts", "name"),
        ("Opportunity", "opportunity", "name"),
        ("Task", "tasks", "title"),
        ("Case", "cases", "name"),
    ],
)
def test_delete_cleans_values_rules_and_order_for_selected_object(
    admin_client, org_a, org_b, target, app, name_key
):
    field = CustomFieldDefinition.objects.create(
        org=org_a,
        target_model=target,
        key="custom_rating",
        label="Rating",
        field_type="number",
    )
    model = apps.get_model(app, target)
    status_fields = {"status": "New", "priority": "Medium"} if target == "Task" else {}
    record = model.objects.create(
        org=org_a,
        **status_fields,
        **{name_key: "Delete value"},
        custom_fields={field.key: 0, "keep": False},
    )
    other_model = Account if target == "Contact" else Contact
    other = other_model.objects.create(org=org_a, custom_fields={field.key: 7})
    with rls_org(org_b):
        foreign = model.objects.create(
            org=org_b,
            **status_fields,
            **{name_key: "Other tenant"},
            custom_fields={field.key: 9},
        )
    reference = "custom_fields." + field.key
    org_a.property_order = {target: [name_key, reference, "last_activity_at"]}
    org_a.pipeline_settings = {
        target: [
            {
                "key": "example",
                "required_fields": [name_key, reference],
                "allowed_from": ["origin"],
            }
        ]
    }
    org_a.save()
    response = admin_client.delete(
        endpoint(field), {"confirmation": field.key}, format="json"
    )
    assert response.status_code == 200, response.content
    assert response.data["records_updated"] == 1
    record.refresh_from_db()
    other.refresh_from_db()
    org_a.refresh_from_db()
    with rls_org(org_b):
        foreign.refresh_from_db()
    assert record.custom_fields == {"keep": False}
    assert other.custom_fields[field.key] == 7 and foreign.custom_fields[field.key] == 9
    assert org_a.property_order[target] == [name_key, "last_activity_at"]
    assert org_a.pipeline_settings[target][0]["required_fields"] == [name_key]
    assert org_a.pipeline_settings[target][0]["allowed_from"] == ["origin"]
    assert not CustomFieldDefinition.objects.filter(pk=field.pk).exists()


def test_turn_off_still_preserves_values_and_definition(admin_client, field, org_a):
    record = Contact.objects.create(org=org_a, custom_fields={field.key: 12})
    assert admin_client.delete(f"/api/custom-fields/{field.pk}/").status_code == 200
    field.refresh_from_db()
    record.refresh_from_db()
    assert not field.is_active and record.custom_fields[field.key] == 12


def test_delete_cannot_reach_another_tenant_or_system_field(admin_client, org_b):
    with rls_org(org_b):
        foreign = CustomFieldDefinition.objects.create(
            org=org_b,
            target_model="Contact",
            key="custom_foreign",
            label="Foreign",
            field_type="text",
        )
    assert (
        admin_client.delete(
            endpoint(foreign), {"confirmation": foreign.key}, format="json"
        ).status_code
        == 404
    )
    assert (
        admin_client.delete(
            f"/api/custom-fields/{uuid4()}/?permanent=true",
            {"confirmation": "phone"},
            format="json",
        ).status_code
        == 404
    )


def test_failed_delete_rolls_back_saved_values(admin_client, field, org_a):
    record = Contact.objects.create(org=org_a, custom_fields={field.key: 10})
    with patch.object(
        CustomFieldDefinition, "delete", side_effect=RuntimeError("Deletion failed")
    ):
        with pytest.raises(RuntimeError):
            admin_client.delete(
                endpoint(field), {"confirmation": field.key}, format="json"
            )
    record.refresh_from_db()
    assert record.custom_fields == {field.key: 10}
    assert CustomFieldDefinition.objects.filter(pk=field.pk).exists()


def test_retired_marketing_property_is_not_offered(admin_client):
    response = admin_client.get("/api/custom-fields/?catalog=true&target_model=Contact")
    assert response.status_code == 200
    assert "do_not_call" not in [row["key"] for row in response.data["properties"]]
    rules = admin_client.get("/api/pipeline-settings/").data["pipelines"]["Contact"][
        "properties"
    ]
    assert "do_not_call" not in [row["key"] for row in rules]
