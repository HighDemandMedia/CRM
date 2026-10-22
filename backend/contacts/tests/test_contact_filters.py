from datetime import datetime, timezone

import pytest

from common.models import Activity
from contacts.models import Contact

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("relation", ["tag", "owner_name", "owner_email", "company"])
def test_search_related_fields_keeps_unique_contacts_and_counts(
    admin_client, admin_profile, user_profile, org_a, relation
):
    from accounts.models import Account
    from common.models import Tags

    needle = "relatedneedle"
    admin_profile.user.name = needle if relation == "owner_name" else "Owner"
    if relation == "owner_email":
        admin_profile.user.email = f"{needle}@example.com"
    admin_profile.user.save()
    contacts = [
        Contact.objects.create(org=org_a, first_name=f"Person {i}", is_active=i == 0)
        for i in range(2)
    ]
    for contact_index, contact in enumerate(contacts):
        contact.assigned_to.add(admin_profile, user_profile)
        for index in range(2):
            contact.tags.add(
                Tags.objects.create(
                    org=org_a,
                    name=f"{needle if relation == 'tag' else 'Tag'}-{contact_index}-{index}",
                )
            )
            company = Account.objects.create(
                org=org_a,
                name=f"{needle if relation == 'company' else 'Company'} {contact.pk} {index}",
            )
            company.contacts.add(contact)

    params = {"search": needle, "compact": "true", "limit": 1}
    response = admin_client.get("/api/contacts/", params)
    assert response.status_code == 200, response.data
    assert response.data["count"] == 2
    assert response.data["active_count"] == 1
    assert response.data["inactive_count"] == 1
    first_id = response.data["results"][0]["id"]
    second = admin_client.get("/api/contacts/", {**params, "offset": 1})
    assert second.status_code == 200, second.data
    assert {first_id, second.data["results"][0]["id"]} == {
        str(contact.pk) for contact in contacts
    }
    active = admin_client.get("/api/contacts/", {**params, "is_active": "true"})
    assert active.data["count"] == 1
    assert active.data["results"][0]["id"] == str(contacts[0].pk)


def test_search_does_not_expand_member_or_tenant_visibility(
    user_client, user_profile, admin_profile, org_a, org_b
):
    from common.models import Tags
    from common.testing import rls_org

    visible = Contact.objects.create(org=org_a, first_name="Visible")
    visible.assigned_to.add(user_profile)
    hidden = Contact.objects.create(org=org_a, first_name="Hidden")
    hidden.assigned_to.add(admin_profile)
    tag = Tags.objects.create(org=org_a, name="needle")
    visible.tags.add(tag)
    hidden.tags.add(tag)
    with rls_org(org_b):
        Contact.objects.create(org=org_b, first_name="needle")
    response = user_client.get(
        "/api/contacts/", {"search": "needle", "compact": "true"}
    )
    assert response.status_code == 200, response.data
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(visible.pk)


def test_search_related_records_stays_in_tenant(admin_client, org_a, org_b, profile_b):
    from accounts.models import Account
    from common.models import Tags
    from common.testing import rls_org

    contact = Contact.objects.create(org=org_a, first_name="Local")
    with rls_org(org_b):
        tag = Tags.objects.create(org=org_b, name="foreignneedle")
        company = Account.objects.create(org=org_b, name="foreignneedle")
    profile_b.user.name = "foreignneedle"
    profile_b.user.save()
    # Simulate legacy malformed links; search must retain its related-org guards.
    Contact.tags.through.objects.create(contact=contact, tags=tag)
    Contact.assigned_to.through.objects.create(contact=contact, profile=profile_b)
    Account.contacts.through.objects.create(contact=contact, account=company)
    response = admin_client.get("/api/contacts/", {"search": "foreignneedle"})
    assert response.status_code == 200, response.data
    assert response.data["count"] == 0


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
