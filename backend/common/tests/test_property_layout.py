import pytest

from common.models import CustomFieldDefinition
from common.property_catalog import FIELDS, properties_for
from common.property_layout import property_key

URL = "/api/property-layout/"


@pytest.mark.django_db
@pytest.mark.parametrize("target", list(FIELDS))
def test_order_mixes_system_custom_and_persists(admin_client, org_a, org_b, target):
    field = CustomFieldDefinition.objects.create(
        org=org_a,
        target_model=target,
        key="custom_test",
        label="Test property",
        field_type="text",
    )
    from common.serializer import CustomFieldDefinitionSerializer

    rows = properties_for(org_a, target, [CustomFieldDefinitionSerializer(field).data])[
        "properties"
    ]
    keys = [property_key(row) for row in rows]
    keys = [keys[-1], *keys[:-1]]
    revision = admin_client.get(URL).json()["revision"]
    response = admin_client.put(
        URL,
        {"target_model": target, "order": keys, "revision": revision},
        format="json",
    )
    assert response.status_code == 200, response.data
    org_a.refresh_from_db()
    org_b.refresh_from_db()
    assert org_a.property_order[target] == keys
    assert not org_b.property_order
    catalog = admin_client.get(
        f"/api/custom-fields/?catalog=true&target_model={target}"
    ).json()
    assert catalog["properties"][0]["key"] == field.key
    assert (
        admin_client.get(URL).json()["objects"][target]["custom"][0]["key"] == field.key
    )
    assert (
        admin_client.put(
            URL,
            {"target_model": target, "order": keys, "revision": revision},
            format="json",
        ).status_code
        == 409
    )


@pytest.mark.django_db
def test_only_admin_and_reject_incomplete_keys(admin_client, user_client):
    assert user_client.get(URL).status_code == 200
    assert user_client.put(URL, {}, format="json").status_code == 403
    revision = admin_client.get(URL).json()["revision"]
    assert (
        admin_client.put(
            URL,
            {"target_model": "Contact", "order": ["first_name"], "revision": revision},
            format="json",
        ).status_code
        == 400
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "target,endpoint,values",
    [
        ("Contact", "contacts", {"first_name": "Test"}),
        ("Account", "accounts", {"name": "Test"}),
        ("Opportunity", "opportunities", {"name": "Test"}),
        ("Task", "tasks", {"title": "Test", "status": "New", "priority": "Medium"}),
        ("Case", "cases", {"name": "Test"}),
    ],
)
def test_custom_property_value_is_saved_and_published(
    admin_client, org_a, target, endpoint, values
):
    from common.property_catalog import target_model

    CustomFieldDefinition.objects.create(
        org=org_a,
        target_model=target,
        key="custom_test",
        label="Test",
        field_type="text",
    )
    record = target_model(target).objects.create(org=org_a, **values)
    response = admin_client.patch(
        f"/api/{endpoint}/{record.pk}/",
        {"custom_fields": {"custom_test": "Saved value"}},
        format="json",
    )
    assert response.status_code == 200, response.data
    record.refresh_from_db()
    assert record.custom_fields["custom_test"] == "Saved value"
