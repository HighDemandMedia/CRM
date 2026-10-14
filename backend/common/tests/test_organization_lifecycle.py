"""Closure must be reversible, tenant-scoped and fail closed on cleanup errors."""

from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from common.attachment_cleanup import purge_files
from common.models import (
    GoogleConnection,
    Org,
    OrganizationClosure,
    OrganizationLifecycleEvent,
    PendingFileDeletion,
    Profile,
    User,
)
from common.organization_lifecycle import (
    change_lifecycle,
    lifecycle_payload,
    organization_job,
)
from common.organization_purge import purge_organization
from contacts.models import Contact


@pytest.fixture
def owner(admin_user, settings):
    settings.CRM_ORG_CLOSURE_ENABLED = True
    settings.CRM_ORG_PURGE_ENABLED = True
    admin_user.is_superuser = True
    admin_user.save(update_fields=["is_superuser"])
    return admin_user


def due(org, owner):
    change_lifecycle(org.pk, owner, "close")
    deadline = timezone.now() - timedelta(seconds=1)
    Org.objects.filter(pk=org.pk).update(deletion_due_at=deadline)
    OrganizationClosure.objects.filter(org_id=org.pk).update(deletion_due_at=deadline)


def test_owner_only_and_gate(org_a, admin_user, settings):
    settings.CRM_ORG_CLOSURE_ENABLED = True
    with pytest.raises(PermissionDenied):
        change_lifecycle(org_a.pk, admin_user, "close")
    admin_user.is_superuser = True
    admin_user.save(update_fields=["is_superuser"])
    settings.CRM_ORG_CLOSURE_ENABLED = False
    with pytest.raises(ValidationError):
        change_lifecycle(org_a.pk, admin_user, "close")
    org_a.refresh_from_db()
    assert org_a.closing_at is None


@pytest.mark.parametrize("action", ["close", "reactivate"])
def test_customer_admin_cannot_control_closure(admin_client, admin_user, org_a, action):
    assert admin_user.is_superuser is False
    response = admin_client.post(
        "/api/org/lifecycle/", {"action": action, "confirmation": org_a.name}
    )
    assert response.status_code == 403
    payload = admin_client.get("/api/org/settings/").data["lifecycle"]
    assert payload["can_manage"] is False
    assert payload["enabled"] is False
    assert payload["can_reactivate"] is False
    assert payload["purge_enabled"] is False
    org_a.refresh_from_db()
    assert org_a.closing_at is None
    assert not OrganizationLifecycleEvent.objects.exists()


def test_recovery_controls_are_owner_only_even_when_closing(org_a, owner, regular_user):
    closed = change_lifecycle(org_a.pk, owner, "close")
    assert lifecycle_payload(closed, owner)["can_reactivate"] is True
    payload = lifecycle_payload(closed, regular_user)
    assert payload["read_only"] is True
    assert payload["can_manage"] is payload["can_reactivate"] is False


def test_revoked_owner_cannot_use_stale_privileges(org_a, owner):
    User.objects.filter(pk=owner.pk).update(is_superuser=False)
    with pytest.raises(PermissionDenied):
        change_lifecycle(org_a.pk, owner, "close")
    assert not OrganizationClosure.objects.exists()


def test_confirmation_uses_current_organization_name(org_a, owner):
    old_name = org_a.name
    Org.objects.filter(pk=org_a.pk).update(name="Renamed organization")
    with pytest.raises(ValidationError):
        change_lifecycle(org_a.pk, owner, "close", confirmation=old_name)
    assert not OrganizationClosure.objects.exists()


def test_organization_owner_can_close_and_reactivate_own_workspace(
    org_a, admin_user, admin_client, settings
):
    settings.CRM_ORG_CLOSURE_ENABLED = True
    Org.objects.filter(pk=org_a.pk).update(owner=admin_user)
    record = Contact.objects.create(org=org_a, first_name="Retained")
    payload = admin_client.get("/api/org/settings/").data["lifecycle"]
    assert payload["can_manage"] is payload["enabled"] is True
    for action in ("close", "reactivate"):
        response = admin_client.post(
            "/api/org/lifecycle/", {"action": action, "confirmation": org_a.name}
        )
        assert response.status_code == 200
        assert response.data["read_only"] is (action == "close")
    assert Contact.objects.filter(pk=record.pk).exists()
    org_a.refresh_from_db()
    assert org_a.closing_at is None


@pytest.mark.parametrize("action", ["close", "reactivate"])
def test_organization_owner_cannot_control_another_workspace(
    org_a, org_b, admin_user, admin_profile, settings, action
):
    from common.testing import rls_org

    settings.CRM_ORG_CLOSURE_ENABLED = True
    Org.objects.filter(pk=org_a.pk).update(owner=admin_user)
    # Even an administrator membership in the other workspace is insufficient.
    with rls_org(org_b):
        Profile.objects.create(org=org_b, user=admin_user, role="ADMIN")
    assert lifecycle_payload(org_b, admin_user)["can_manage"] is False
    with pytest.raises(PermissionDenied):
        change_lifecycle(org_b.pk, admin_user, action)
    assert not OrganizationLifecycleEvent.objects.filter(org_id=org_b.pk).exists()


def test_removed_owner_membership_cannot_manage_closure(
    org_a, admin_user, admin_profile, settings
):
    settings.CRM_ORG_CLOSURE_ENABLED = True
    Org.objects.filter(pk=org_a.pk).update(owner=admin_user)
    Profile.objects.filter(pk=admin_profile.pk).update(removed_at=timezone.now())
    org_a.refresh_from_db()
    assert lifecycle_payload(org_a, admin_user)["can_manage"] is False
    with pytest.raises(PermissionDenied):
        change_lifecycle(org_a.pk, admin_user, "close")


def test_close_reactivate_preserves_data_and_disconnects_google(
    org_a, admin_profile, owner, settings
):
    record = Contact.objects.create(org=org_a, first_name="Retained")
    conn = GoogleConnection.objects.create(
        org=org_a,
        profile=admin_profile,
        service="calendar",
        status="connected",
        encrypted_refresh_token="ciphertext",
        oauth_state_hash="pending",
    )
    original_generation = conn.generation
    closed = change_lifecycle(org_a.pk, owner, "close")
    assert closed.deletion_due_at - closed.closing_at == timedelta(days=30)
    assert (
        change_lifecycle(org_a.pk, owner, "close").deletion_due_at
        == closed.deletion_due_at
    )
    conn.refresh_from_db()
    assert conn.status == "disconnected"
    assert conn.encrypted_refresh_token == conn.oauth_state_hash == ""
    assert conn.generation != original_generation
    # Disabling new closures must not strand a customer within the recovery window.
    settings.CRM_ORG_CLOSURE_ENABLED = False
    restored = change_lifecycle(org_a.pk, owner, "reactivate")
    assert restored.closing_at is None and restored.deletion_due_at is None
    assert Contact.objects.filter(pk=record.pk).exists()
    assert OrganizationClosure.objects.get(org_id=org_a.pk).reactivated_at
    assert list(
        OrganizationLifecycleEvent.objects.order_by("pk").values_list(
            "action", flat=True
        )
    ) == ["close", "reactivate"]
    assert not purge_organization(org_a.pk)


def test_boundary_prevents_reactivation(org_a, owner):
    due(org_a, owner)
    with pytest.raises(ValidationError):
        change_lifecycle(org_a.pk, owner, "reactivate")


def test_read_export_boundary_and_forged_actions(
    admin_client, user_client, org_a, owner
):
    assert (
        user_client.post(
            "/api/org/lifecycle/", {"action": "close", "confirmation": org_a.name}
        ).status_code
        == 403
    )
    assert (
        admin_client.post(
            "/api/org/lifecycle/", {"action": "close", "confirmation": "wrong"}
        ).status_code
        == 400
    )
    assert (
        admin_client.post(
            "/api/org/lifecycle/", {"action": "close", "confirmation": org_a.name}
        ).status_code
        == 200
    )
    assert admin_client.get("/api/contacts/").status_code == 200
    assert (
        admin_client.get("/api/org/ui-context/").data["lifecycle"]["read_only"] is True
    )
    assert (
        admin_client.post("/api/contacts/", {"first_name": "Blocked"}).status_code
        == 403
    )
    assert (
        admin_client.patch("/api/org/settings/", {"name": "Blocked"}).status_code == 403
    )
    assert (
        admin_client.get("/api/integrations/google/connect/calendar/").status_code
        == 403
    )
    assert (
        admin_client.post(
            "/api/org/lifecycle/", {"action": "reactivate", "confirmation": org_a.name}
        ).status_code
        == 200
    )
    assert (
        admin_client.get("/api/org/ui-context/").data["lifecycle"]["read_only"] is False
    )


def test_queued_job_and_public_submission_are_blocked(
    org_a, owner, unauthenticated_client
):
    @organization_job
    def work(org_id):
        raise AssertionError("Job ran after closure")

    change_lifecycle(org_a.pk, owner, "close")
    assert work(str(org_a.pk)) is None
    from uuid import uuid4

    result = unauthenticated_client.post(
        f"/api/public/forms/{org_a.pk}/{uuid4()}/submit/", {}
    )
    assert result.status_code == 404


def test_purge_preserves_other_tenant_and_shared_user(
    org_a, org_b, admin_profile, owner
):
    from common.testing import rls_org

    target = Contact.objects.create(org=org_a, first_name="Remove")
    with rls_org(org_b):
        retained = Contact.objects.create(org=org_b, first_name="Keep")
        shared = Profile.objects.create(org=org_b, user=owner, role="ADMIN")
    due(org_a, owner)
    assert purge_organization(org_a.pk)
    assert not Org.objects.filter(pk=org_a.pk).exists()
    assert not Contact.objects.filter(pk=target.pk).exists()
    with rls_org(org_b):
        assert Contact.objects.filter(pk=retained.pk).exists()
        assert Profile.objects.filter(pk=shared.pk).exists()
    assert User.objects.filter(pk=owner.pk).exists()
    assert OrganizationClosure.objects.get(org_id=org_a.pk).data_deleted_at
    assert purge_organization(org_a.pk)  # idempotent retry


def test_purge_files_retry_and_rollback(org_a, owner):
    org_a.logo.save("lifecycle-test.png", ContentFile(b"demo"))
    key = org_a.logo.name
    due(org_a, owner)
    with pytest.raises(RuntimeError), transaction.atomic():
        purge_organization(org_a.pk)
        raise RuntimeError("rollback")
    assert Org.objects.filter(pk=org_a.pk).exists()
    assert not PendingFileDeletion.objects.filter(name=key).exists()
    assert purge_organization(org_a.pk)
    assert PendingFileDeletion.objects.filter(name=key, org_id=org_a.pk).exists()
    with patch("common.attachment_cleanup.default_storage.delete", side_effect=OSError):
        purge_files()
    receipt = OrganizationClosure.objects.get(org_id=org_a.pk)
    assert receipt.files_deleted_at is None
    assert PendingFileDeletion.objects.filter(name=key, attempts=1).exists()
    purge_files()
    receipt.refresh_from_db()
    assert receipt.files_deleted_at is not None
    assert not org_a.logo.storage.exists(key)


def test_command_dry_run_gate_and_not_due(org_a, owner, settings):
    change_lifecycle(org_a.pk, owner, "close")
    assert not purge_organization(org_a.pk)
    due(org_a, owner)
    call_command("purge_closed_organizations", stdout=StringIO())
    assert Org.objects.filter(pk=org_a.pk).exists()
    settings.CRM_ORG_PURGE_ENABLED = False
    with pytest.raises(CommandError):
        call_command("purge_closed_organizations", execute=True)
    assert not purge_organization(org_a.pk)


def test_scheduled_purge_waits_for_deadline_and_preserves_reactivated_org(
    org_a, org_b, owner
):
    from common.tasks import purge_closed_organizations
    from common.testing import rls_org

    target = Contact.objects.create(org=org_a, first_name="Closed workspace")
    with rls_org(org_b):
        retained = Contact.objects.create(org=org_b, first_name="Reactivated workspace")
    change_lifecycle(org_a.pk, owner, "close")
    change_lifecycle(org_b.pk, owner, "close")
    change_lifecycle(org_b.pk, owner, "reactivate")
    purge_closed_organizations.run()
    assert Org.objects.filter(pk=org_a.pk).exists()
    with rls_org(org_a):
        assert Contact.objects.filter(pk=target.pk).exists()

    due(org_a, owner)
    purge_closed_organizations.run()
    assert not Org.objects.filter(pk=org_a.pk).exists()
    with rls_org(org_a):
        assert not Contact.objects.filter(pk=target.pk).exists()
    with rls_org(org_b):
        assert Contact.objects.filter(pk=retained.pk).exists()
    assert Org.objects.filter(pk=org_b.pk, closing_at__isnull=True).exists()
    assert OrganizationClosure.objects.get(org_id=org_a.pk).data_deleted_at


def test_shared_storage_key_survives_other_tenant_cleanup(org_a, org_b, owner):
    org_a.logo.save("shared-logo.png", ContentFile(b"shared demo logo"))
    key = org_a.logo.name
    org_b.logo = key
    org_b.save(update_fields=["logo"])
    due(org_a, owner)
    assert purge_organization(org_a.pk)
    purge_files()
    assert org_b.logo.storage.exists(key)
    assert not PendingFileDeletion.objects.filter(org_id=org_a.pk).exists()


def test_purge_handles_protected_relations(org_a, owner, admin_profile):
    from accounts.models import Account
    from cases.models import Case, TimeEntry
    from common.models import OrganizationInvitation, SalesAppointment
    from common.rbac import ensure_default_roles
    from invoices.models import Invoice

    role = ensure_default_roles(org_a)[0]
    admin_profile.access_role = role
    admin_profile.save()
    OrganizationInvitation.objects.create(
        org=org_a,
        email="invited@example.com",
        access_role=role,
        token_hash="unused-token",
        expires_at=timezone.now() + timedelta(days=1),
    )
    now = timezone.now()
    SalesAppointment.objects.create(
        org=org_a,
        title="Demo",
        host=admin_profile,
        created_by=owner,
        starts_at=now,
        ends_at=now + timedelta(hours=1),
    )
    case = Case.objects.create(org=org_a, name="Demo")
    TimeEntry.objects.create(
        org=org_a, case=case, profile=admin_profile, started_at=now
    )
    account = Account.objects.create(org=org_a, name="Demo")
    Invoice.objects.create(
        org=org_a,
        account=account,
        invoice_title="Historical",
        invoice_number="DEMO-TEST",
    )
    due(org_a, owner)
    assert purge_organization(org_a.pk)
    assert not Org.objects.filter(pk=org_a.pk).exists()


@pytest.mark.postgres_only
@pytest.mark.django_db(transaction=True)
def test_closure_waits_for_inflight_job_and_blocks_new_work(org_a, owner):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from django.db import connections

    from common.organization_lifecycle import organization_lock

    started = Event()

    def close():
        try:
            started.set()
            return change_lifecycle(org_a.pk, owner, "close")
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with organization_lock(org_a.pk, transactional=False):
            future = pool.submit(close)
            assert started.wait(timeout=5)
            # Force PostgreSQL to observe that the closer is waiting on our lock.
            import time

            from django.db import connection

            end = time.monotonic() + 5
            waiting = False
            while time.monotonic() < end:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT EXISTS (SELECT 1 FROM pg_locks WHERE locktype='advisory' AND NOT granted)"
                    )
                    waiting = cursor.fetchone()[0]
                if waiting:
                    break
                time.sleep(0.02)
            assert waiting and not future.done()
        assert future.result(timeout=10).closing_at
    assert Org.objects.get(pk=org_a.pk).closing_at


def test_export_permissions_remain_unchanged_while_write_permissions_are_removed(
    org_a, owner, admin_profile
):
    from common.views.role_views import permissions_payload

    before = permissions_payload(admin_profile)
    change_lifecycle(org_a.pk, owner, "close")
    admin_profile.refresh_from_db()
    after = permissions_payload(admin_profile)
    assert after["rules"]["contacts"]["export"] == before["rules"]["contacts"]["export"]
    assert after["rules"]["contacts"]["view"] == before["rules"]["contacts"]["view"]
    assert after["rules"]["contacts"]["create"] == "none"
