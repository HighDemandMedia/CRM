"""Attachment deletion is a distinct, tenant- and record-scoped capability."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import Account
from cases.models import Case
from common.attachment_cleanup import purge_files
from common.models import Attachments, CRMRole, PendingFileDeletion, Teams
from common.rbac import default_rules, expanded_rules, validate_rules
from common.serializer import AttachmentsSerializer
from common.testing import rls_org
from contacts.models import Contact
from opportunity.models import Opportunity
from tasks.models import Task

pytestmark = pytest.mark.django_db
OBJECTS = [
    (Contact, "contacts", "contacts", "first_name"),
    (Account, "companies", "accounts", "name"),
    (Opportunity, "deals", "opportunities", "name"),
    (Task, "tasks", "tasks", "title"),
    (Case, "tickets", "cases", "name"),
]


def role_for(profile, module="contacts", scope="own", grant=False):
    rules = default_rules(scope)
    if grant:
        rules[module]["delete_attachments"] = scope
    role = CRMRole.objects.create(
        org=profile.org, name=f"Files {uuid4()}", scope=scope, rules=rules
    )
    profile.access_role = role
    profile.save()
    return role


def attachment(parent, user):
    item = Attachments.objects.create(
        org=parent.org,
        content_type=ContentType.objects.get_for_model(parent),
        object_id=parent.pk,
        file_name="proposal.txt",
        attachment=SimpleUploadedFile("proposal.txt", b"private proposal"),
    )
    Attachments.objects.filter(pk=item.pk).update(created_by=user)
    item.refresh_from_db()
    return item


@pytest.fixture(autouse=True)
def isolated_files(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.mark.parametrize("model,module,endpoint,field", OBJECTS)
@pytest.mark.parametrize("legacy", [False, True])
def test_grant_revoke_and_delete_file(
    user_client, user_profile, admin_user, org_a, model, module, endpoint, field, legacy
):
    role = role_for(user_profile, module)
    parent = model.objects.create(org=org_a, **{field: "Owned record"})
    parent.assigned_to.add(user_profile)
    item = attachment(parent, admin_user)
    url = (
        f"/api/{endpoint}/attachment/{item.pk}/"
        if legacy
        else f"/api/attachments/{item.pk}/"
    )
    storage, name = item.attachment.storage, item.attachment.name
    assert user_client.delete(url).status_code == 403
    assert storage.exists(name)
    assert Attachments.objects.filter(pk=item.pk).exists()
    # Upload and delete-record permission are independent of attachment deletion.
    role.rules[module]["delete_attachments"] = "own"
    role.rules[module]["attachments"] = "none"
    role.save()
    response = user_client.delete(url)
    assert response.status_code == 200, response.data
    assert not Attachments.objects.filter(pk=item.pk).exists()
    assert PendingFileDeletion.objects.filter(name=name).exists()
    purge_files()
    assert not storage.exists(name)
    assert model.objects.filter(pk=parent.pk).exists()
    assert user_client.delete(url).status_code == 404
    # A previously granted action can be revoked without ending the session.
    another = attachment(parent, user_profile.user)
    role.rules[module]["delete_attachments"] = "none"
    role.save()
    assert user_client.delete(f"/api/attachments/{another.pk}/").status_code == 403
    assert another.attachment.storage.exists(another.attachment.name)


@pytest.mark.parametrize(
    "scope,allowed", [("own", False), ("team", True), ("organization", True)]
)
def test_scope_is_parent_record_not_uploader(
    user_client, user_profile, admin_profile, org_a, scope, allowed
):
    role_for(user_profile, scope=scope, grant=True)
    team = Teams.objects.create(org=org_a, name="Sales")
    team.users.add(user_profile, admin_profile)
    parent = Contact.objects.create(org=org_a, first_name="Colleague's record")
    parent.assigned_to.add(admin_profile)
    item = attachment(parent, user_profile.user)
    response = user_client.delete(f"/api/attachments/{item.pk}/")
    assert response.status_code == (200 if allowed else 403), response.data


def test_admin_cross_org_parent_and_legacy_route_isolation(
    admin_client, admin_user, org_a, org_b
):
    admin_user.is_superuser = True
    admin_user.save(update_fields=["is_superuser"])
    with rls_org(org_b):
        other = Contact.objects.create(org=org_b, first_name="Other tenant")
        foreign = attachment(other, admin_user)
    assert admin_client.delete(f"/api/attachments/{foreign.pk}/").status_code == 404
    parent = Contact.objects.create(org=org_a, first_name="Local")
    broken = attachment(parent, admin_user)
    Attachments.objects.filter(pk=broken.pk).update(object_id=other.pk)
    assert admin_client.delete(f"/api/attachments/{broken.pk}/").status_code == 403
    local = attachment(parent, admin_user)
    # Preview endpoints cannot bypass a core object's permission or type check.
    for endpoint in (
        "leads/attachment",
        "opportunities/attachment",
        "tasks/attachment",
        "invoices/attachments",
    ):
        assert admin_client.delete(f"/api/{endpoint}/{local.pk}/").status_code == 404
    assert admin_client.delete(f"/api/attachments/{local.pk}/").status_code == 200


def test_storage_failure_keeps_cleanup_receipt_for_retry(
    admin_client, admin_user, org_a
):
    parent = Contact.objects.create(org=org_a, first_name="Retry")
    item = attachment(parent, admin_user)
    with patch.object(
        item.attachment.storage, "delete", side_effect=OSError("Storage unavailable")
    ):
        assert admin_client.delete(f"/api/attachments/{item.pk}/").status_code == 200
        purge_files()
    assert not Attachments.objects.filter(pk=item.pk).exists()
    assert PendingFileDeletion.objects.filter(name=item.attachment.name).exists()
    assert item.attachment.storage.exists(item.attachment.name)
    purge_files()
    assert not item.attachment.storage.exists(item.attachment.name)
    assert not PendingFileDeletion.objects.exists()


def test_catalog_defaults_and_legacy_policy(admin_client):
    for scope in ("own", "team", "organization"):
        rules = default_rules(scope)
        for module in ("contacts", "companies", "deals", "tasks", "tickets"):
            assert rules[module]["delete_attachments"] == "none"
            rules[module].pop("delete_attachments")
        expanded = expanded_rules(rules, scope)
        assert expanded["contacts"]["delete_attachments"] == "none"
        validate_rules(expanded)
    catalog = admin_client.get("/api/roles/").data["catalog"]
    for module in catalog[:5]:
        assert "delete_attachments" in {action["key"] for action in module["actions"]}


def test_can_delete_reflects_current_record_scope(
    user_client, user_profile, admin_user, org_a
):
    role = role_for(user_profile)
    parent = Contact.objects.create(org=org_a, first_name="Visible")
    parent.assigned_to.add(user_profile)
    item = attachment(parent, admin_user)
    url = f"/api/contacts/{parent.pk}/"
    assert user_client.get(url).data["attachments"][0]["can_delete"] is False
    role.rules["contacts"]["delete_attachments"] = "own"
    role.save()
    assert user_client.get(url).data["attachments"][0]["can_delete"] is True
    # Serialization without an authenticated request must not invent a grant.
    assert AttachmentsSerializer(item).data["can_delete"] is False


def test_dangling_parent_and_anonymous_are_denied(
    admin_client, admin_user, unauthenticated_client, org_a
):
    parent = Contact.objects.create(org=org_a, first_name="Missing")
    item = attachment(parent, admin_user)
    assert unauthenticated_client.delete(
        f"/api/attachments/{item.pk}/"
    ).status_code in (401, 403)
    Attachments.objects.filter(pk=item.pk).update(object_id=uuid4())
    assert admin_client.delete(f"/api/attachments/{item.pk}/").status_code == 403


def test_database_rollback_preserves_attachment_and_file(admin_user, org_a):
    from django.db import transaction

    parent = Contact.objects.create(org=org_a, first_name="Rollback")
    item = attachment(parent, admin_user)
    pk, name = item.pk, item.attachment.name
    with pytest.raises(RuntimeError), transaction.atomic():
        item.delete()
        raise RuntimeError("Database operation failed")
    assert Attachments.objects.filter(pk=pk).exists()
    assert item.attachment.storage.exists(name)
    assert not PendingFileDeletion.objects.filter(name=name).exists()


def test_cleanup_retry_cannot_delete_a_new_upload_with_the_same_name(admin_user, org_a):
    parent = Contact.objects.create(org=org_a, first_name="Reupload")
    old = attachment(parent, admin_user)
    storage, old_name = old.attachment.storage, old.attachment.name
    old.delete()
    # Simulate a crash after storage accepted deletion but before DB acknowledgement.
    storage.delete(old_name)
    new = attachment(parent, admin_user)
    assert new.attachment.name != old_name
    purge_files()
    assert storage.exists(new.attachment.name)
    assert not PendingFileDeletion.objects.exists()


@pytest.mark.parametrize("model,module,endpoint,field", OBJECTS)
def test_parent_deletion_collects_files(
    admin_user, org_a, model, module, endpoint, field
):
    parent = model.objects.create(org=org_a, **{field: "Delete parent"})
    item = attachment(parent, admin_user)
    name = item.attachment.name
    parent.delete()
    assert not Attachments.objects.filter(pk=item.pk).exists()
    assert PendingFileDeletion.objects.filter(name=name).exists()
    assert item.attachment.storage.exists(name)
    purge_files()
    assert not item.attachment.storage.exists(name)
