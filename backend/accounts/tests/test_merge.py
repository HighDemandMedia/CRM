from datetime import timedelta

import pytest
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from accounts.models import Account
from cases.models import Case
from common.models import Activity, Attachments, Comment, SalesAppointment, Tags
from common.usage_limits import resource_count
from contacts.models import Contact
from opportunity.models import Opportunity
from tasks.models import Task

pytestmark = pytest.mark.django_db


def pair(org):
    return (
        Account.objects.create(org=org, name="Primary Co", email="a@example.com"),
        Account.objects.create(org=org, name="Secondary Co", email="b@example.com"),
    )


def preview(client, a, b):
    response = client.get(f"/api/accounts/{a.pk}/merge/", {"secondary": str(b.pk)})
    assert response.status_code == 200, response.data
    return response.data


def merge(client, a, plan, **kwargs):
    return client.post(
        f"/api/accounts/{a.pk}/merge/",
        {
            "token": plan["token"],
            "confirm": True,
            **kwargs,
        },
        format="json",
    )


def test_merge_values_archive_old_links_and_capacity(admin_client, org_a):
    a, b = pair(org_a)
    created = a.created_at
    plan = preview(admin_client, a, b)
    response = merge(
        admin_client, a, plan, choices={"name": "secondary", "email": "secondary"}
    )
    assert response.status_code == 200, response.data
    a.refresh_from_db()
    b = Account.all_objects.get(pk=b.pk)
    assert a.name == "Secondary Co" and a.email == "b@example.com"
    assert a.created_at == created and b.merged_into_id == a.pk and b.merged_at
    assert b.merge_snapshot["primary"]["name"] == "Primary Co"
    assert not Account.objects.filter(pk=b.pk).exists()
    assert resource_count(org_a.pk, "companies") == 1
    response = admin_client.get(f"/api/accounts/{b.pk}/")
    assert response.status_code == 200, response.data
    assert response.data["account_obj"]["id"] == str(a.pk)
    assert (
        admin_client.patch(
            f"/api/accounts/{b.pk}/", {"name": "Blocked"}, format="json"
        ).status_code
        == 404
    )
    assert merge(admin_client, a, plan).status_code == 200
    assert (
        Activity.objects.filter(
            entity_id=a.pk, metadata__merge__source_id=str(b.pk)
        ).count()
        == 1
    )
    # Archiving releases the former company's name for legitimate future records.
    Account.objects.create(org=org_a, name="Primary Co")


def test_preserves_relationships_notes_files_and_appointments(
    admin_client, admin_profile, admin_user, org_a
):
    a, b = pair(org_a)
    contact = Contact.objects.create(org=org_a, first_name="Customer", account=b)
    a.contacts.add(contact)
    b.contacts.add(contact)
    deal = Opportunity.objects.create(org=org_a, name="Deal", account=b)
    task = Task.objects.create(org=org_a, title="Task", account=b)
    ticket = Case.objects.create(org=org_a, name="Ticket", account=b)
    tag = Tags.objects.create(org=org_a, name="VIP")
    b.tags.add(tag)
    b.assigned_to.add(admin_profile)
    b.description = "Original company notes"
    b.save()
    ct = ContentType.objects.get_for_model(Account)
    note = Comment.objects.create(
        org=org_a,
        content_type=ct,
        object_id=b.pk,
        comment="Keep",
        commented_by=admin_profile,
    )
    file = Attachments.objects.create(
        org=org_a,
        content_type=ct,
        object_id=b.pk,
        file_name="file.pdf",
        attachment="existing/file.pdf",
    )
    start = timezone.now() + timedelta(days=1)
    event = SalesAppointment.objects.create(
        org=org_a,
        title="Meeting",
        host=admin_profile,
        created_by=admin_user,
        company=b,
        starts_at=start,
        ends_at=start + timedelta(minutes=30),
    )
    event.companies.add(a, b)
    response = merge(admin_client, a, preview(admin_client, a, b))
    assert response.status_code == 200, response.data
    for record in (contact, deal, task, ticket):
        record.refresh_from_db()
        assert record.account_id == a.pk
    note.refresh_from_db()
    file.refresh_from_db()
    event.refresh_from_db()
    a.refresh_from_db()
    assert list(a.contacts.values_list("pk", flat=True)) == [contact.pk]
    assert note.object_id == a.pk and note.commented_by_id == admin_profile.pk
    assert file.object_id == a.pk and file.attachment.name == "existing/file.pdf"
    assert event.company_id == a.pk and list(
        event.companies.values_list("pk", flat=True)
    ) == [a.pk]
    assert a.appointment_at == start
    assert (
        a.tags.filter(pk=tag.pk).exists()
        and a.assigned_to.filter(pk=admin_profile.pk).exists()
    )
    assert Comment.objects.filter(object_id=a.pk, comment=b.description).exists()


def test_admin_only_and_same_org(admin_client, user_client, org_a, org_b):
    a, b = pair(org_a)
    other = Account.objects.create(org=org_b, name="Other tenant")
    assert (
        user_client.get(f"/api/accounts/{a.pk}/merge/", {"q": "Secondary"}).status_code
        == 403
    )
    plan = preview(admin_client, a, b)
    assert merge(user_client, a, plan).status_code == 403
    assert (
        admin_client.get(
            f"/api/accounts/{a.pk}/merge/", {"secondary": str(other.pk)}
        ).status_code
        == 404
    )
    assert (
        admin_client.get(
            f"/api/accounts/{a.pk}/merge/", {"secondary": str(a.pk)}
        ).status_code
        == 400
    )
    assert (
        admin_client.get(
            f"/api/accounts/{a.pk}/merge/", {"secondary": "invalid"}
        ).status_code
        == 400
    )


def test_stale_tampered_and_unconfirmed_plans_rejected(admin_client, org_a):
    a, b = pair(org_a)
    plan = preview(admin_client, a, b)
    assert merge(admin_client, a, plan, confirm=False).status_code == 400
    assert merge(admin_client, a, {"token": "invalid"}).status_code == 400
    assert merge(admin_client, a, plan, choices={"org": "secondary"}).status_code == 400
    b.city = "Miami"
    b.save()
    assert merge(admin_client, a, plan).status_code == 400
    assert Account.objects.filter(pk=b.pk).exists()


def test_company_stage_rules_roll_back_merge(admin_client, org_a):
    from common.tests.test_pipeline_settings import configure

    a, b = pair(org_a)
    b.stage = "QUALIFIED"
    b.save()
    assert (
        configure(
            admin_client,
            "Account",
            lambda rows: next(r for r in rows if r["key"] == "QUALIFIED").update(
                required_fields=["city"]
            ),
        ).status_code
        == 200
    )
    response = merge(
        admin_client, a, preview(admin_client, a, b), choices={"stage": "secondary"}
    )
    assert response.status_code == 400, response.data
    assert "stage_requirements" in response.data
    a.refresh_from_db()
    b.refresh_from_db()
    assert a.stage == "LEAD" and b.merged_at is None


def test_company_search_excludes_other_tenants_and_archived(admin_client, org_a, org_b):
    a, b = pair(org_a)
    Account.objects.create(org=org_b, name="Secondary Other")
    response = admin_client.get(f"/api/accounts/{a.pk}/merge/", {"q": "Secondary"})
    assert [row["id"] for row in response.data["results"]] == [str(b.pk)]
    assert merge(admin_client, a, preview(admin_client, a, b)).status_code == 200
    assert (
        admin_client.get(f"/api/accounts/{a.pk}/merge/", {"q": "Secondary"}).data[
            "results"
        ]
        == []
    )
