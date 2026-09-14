import pytest

from common.models import Activity
from contacts.models import Contact

pytestmark = pytest.mark.django_db


def test_colored_tags_create_assign_read_remove(admin_client, org_a):
    response = admin_client.post(
        "/api/tags/", {"name": "VIP contact", "color": "purple"}, format="json"
    )
    assert response.status_code == 201, response.data
    tag = response.data["tag"]
    assert tag["color"] == "purple"
    response = admin_client.post(
        "/api/contacts/",
        {
            "name": "Tagged contact",
            "phone": "3055550101",
            "source": "META",
            "stage": "LEAD",
            "tags": [tag["id"]],
        },
        format="json",
    )
    assert response.status_code == 200, response.data
    contact = Contact.objects.get(first_name="Tagged contact")
    row = next(
        row
        for row in admin_client.get("/api/contacts/").data["results"]
        if str(row["id"]) == str(contact.id)
    )
    assert row["tag_details"][0]["color"] == "purple"
    assert row["tag_details"][0]["name"] == "VIP contact"
    url = f"/api/contacts/{contact.id}/"
    assert admin_client.patch(url, {"city": "Miami"}, format="json").status_code == 200
    assert contact.tags.count() == 1
    assert admin_client.patch(url, {"tags": []}, format="json").status_code == 200
    assert contact.tags.count() == 0
    assert Activity.objects.filter(
        entity_id=contact.id, description__icontains="tags"
    ).exists()


def test_member_cannot_create_tags(user_client):
    response = user_client.post(
        "/api/tags/", {"name": "Restricted", "color": "red"}, format="json"
    )
    assert response.status_code == 403
