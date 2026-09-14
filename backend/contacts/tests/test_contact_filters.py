from datetime import datetime, timezone

import pytest

from common.models import Activity
from contacts.models import Contact

pytestmark = pytest.mark.django_db


def test_combined_contact_filters(admin_client, admin_profile, org_a):
    contact = Contact.objects.create(
        first_name="Find me", phone="5550100", stage="LEAD", org=org_a
    )
    contact.assigned_to.add(admin_profile)
    Contact.objects.filter(pk=contact.pk).update(
        created_at=datetime(2026, 9, 1, 12, tzinfo=timezone.utc)
    )
    Activity.objects.filter(entity_id=contact.pk).delete()
    activity = Activity.objects.create(
        org=org_a,
        entity_type="Contact",
        entity_id=contact.pk,
        entity_name=contact.name,
        action="UPDATE",
        description="Test activity",
    )
    Activity.objects.filter(pk=activity.pk).update(
        created_at=datetime(2026, 9, 5, 12, tzinfo=timezone.utc)
    )
    Contact.objects.create(first_name="Other", phone="5550200", stage="LOST", org=org_a)
    params = {
        "search": "5550100",
        "assigned_to": str(admin_profile.pk),
        "stage": "LEAD",
        "created_at__gte": "2026-09-01",
        "created_at__lte": "2026-09-01",
        "last_activity_at__gte": "2026-09-05",
        "last_activity_at__lte": "2026-09-05",
    }
    response = admin_client.get("/api/contacts/", params)
    assert response.status_code == 200, response.data
    assert response.data["count"] == 1
    assert str(response.data["results"][0]["id"]) == str(contact.pk)
    assert response.data["results"][0]["last_activity_at"].startswith("2026-09-05")
    params["last_activity_at__gte"] = "2026-09-06"
    assert admin_client.get("/api/contacts/", params).data["count"] == 0


def test_latest_activity_wins_and_creation_is_fallback(admin_client, org_a):
    contact = Contact.objects.create(first_name="Legacy", org=org_a)
    Contact.objects.filter(pk=contact.pk).update(
        created_at=datetime(2026, 8, 1, tzinfo=timezone.utc)
    )
    Activity.objects.filter(entity_id=contact.pk).delete()
    response = admin_client.get(
        "/api/contacts/", {"last_activity_at__lte": "2026-08-01"}
    )
    assert response.data["count"] == 1
    for day in [2, 7]:
        event = Activity.objects.create(
            org=org_a,
            entity_type="Contact",
            entity_id=contact.pk,
            entity_name=contact.name,
            action="UPDATE",
            description="Test",
        )
        Activity.objects.filter(pk=event.pk).update(
            created_at=datetime(2026, 9, day, tzinfo=timezone.utc)
        )
    response = admin_client.get(
        "/api/contacts/", {"last_activity_at__lte": "2026-09-03"}
    )
    assert response.data["count"] == 0


@pytest.mark.parametrize(
    "search",
    ["special note", "Boston", "02110", "Organic", "Qualified", "SMS", "vip-filter"],
)
def test_search_contact_properties(admin_client, org_a, search):
    from common.models import Tags

    contact = Contact.objects.create(
        first_name="Search test",
        org=org_a,
        description="special note",
        city="Boston",
        postcode="02110",
        source="ORGANIC",
        stage="QUALIFIED",
        preferred_communication_channel="SMS",
    )
    contact.tags.add(Tags.objects.create(name="vip-filter", org=org_a))
    response = admin_client.get("/api/contacts/", {"search": search})
    assert response.status_code == 200, response.data
    assert response.data["count"] == 1
    assert str(response.data["results"][0]["id"]) == str(contact.pk)


def test_extra_property_filters_combine(admin_client, org_a):
    Contact.objects.create(
        first_name="Matches",
        org=org_a,
        city="Boston",
        postcode="02110",
        source="ORGANIC",
        preferred_communication_channel="SMS",
        do_not_call=True,
    )
    Contact.objects.create(
        first_name="Other",
        org=org_a,
        city="Boston",
        postcode="02110",
        source="META",
        preferred_communication_channel="SMS",
    )
    response = admin_client.get(
        "/api/contacts/",
        {
            "city": "Boston",
            "postcode": "02110",
            "source": "ORGANIC",
            "preferred_communication_channel": "SMS",
            "do_not_call": "true",
        },
    )
    assert response.status_code == 200, response.data
    assert response.data["count"] == 1
