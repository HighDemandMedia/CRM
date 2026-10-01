import pytest

from contacts.models import Contact

pytestmark = pytest.mark.django_db
URL = "/api/contacts/duplicates/"


def test_email_and_formatted_phone_matches_are_scoped(admin_client, org_a, org_b):
    contact = Contact.objects.create(
        org=org_a,
        first_name="Jane Doe",
        email="jane@example.com",
        phone="+1 (305) 555-0199",
    )
    Contact.objects.create(
        org=org_b,
        first_name="Private Jane",
        email="jane@example.com",
        phone="+1 (305) 555-0199",
    )
    response = admin_client.get(
        URL, {"email": " JANE@example.com ", "phone": "13055550199"}
    )
    assert response.status_code == 200, response.data
    assert len(response.data["results"]) == 1
    row = response.data["results"][0]
    assert row["id"] == str(contact.pk)
    assert row["reasons"] == ["Same email", "Same phone"]
    assert admin_client.get(URL, {"phone": "0013055550199"}).data["results"][0][
        "id"
    ] == str(contact.pk)


def test_possible_local_number_is_labelled_and_country_codes_are_preserved(
    admin_client, org_a
):
    contact = Contact.objects.create(
        org=org_a, first_name="Shared phone", phone="+1 305 555 0199"
    )
    row = admin_client.get(URL, {"phone": "305-555-0199"}).data["results"][0]
    assert row["id"] == str(contact.pk)
    assert row["reasons"] == ["Similar phone — check country code"]
    assert admin_client.get(URL, {"phone": "+44 305 555 0199"}).data["results"] == []


def test_names_are_suggestions_not_unique_and_results_are_limited(admin_client, org_a):
    for i in range(8):
        Contact.objects.create(org=org_a, first_name="Alex", last_name=f"Smith {i}")
    result = admin_client.get(URL, {"name": "Alex Smith"}).data["results"]
    assert len(result) == 5
    assert all("Similar name" in row["reasons"] for row in result)
    assert admin_client.get(URL, {"name": "Al"}).data["results"] == []
    assert admin_client.get(URL).data["results"] == []


def test_own_record_is_excluded(admin_client, org_a):
    contact = Contact.objects.create(
        org=org_a, first_name="Existing", email="existing@example.com"
    )
    assert (
        admin_client.get(
            URL, {"email": contact.email, "exclude": str(contact.pk)}
        ).data["results"]
        == []
    )
    assert admin_client.get(URL, {"exclude": "bad"}).status_code == 400


def test_member_cannot_see_other_users_contacts(user_client, org_a):
    Contact.objects.create(
        org=org_a, first_name="Private record", email="private@example.com"
    )
    assert user_client.get(URL, {"email": "private@example.com"}).data["results"] == []


def test_phone_key_updates_on_edit_without_exposing_internal_audit_field(
    admin_client, org_a
):
    contact = Contact.objects.create(
        org=org_a, first_name="Phone edit", phone="+1 305 555 0100"
    )
    response = admin_client.patch(
        f"/api/contacts/{contact.pk}/", {"phone": "+1 (305) 555-0199"}, format="json"
    )
    assert response.status_code == 200, response.data
    contact.refresh_from_db()
    assert contact.phone_match_key == "13055550199"
    assert admin_client.get(URL, {"phone": "13055550100"}).data["results"] == []
    assert admin_client.get(URL, {"phone": "13055550199"}).data["results"][0][
        "id"
    ] == str(contact.pk)
