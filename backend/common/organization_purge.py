"""Tenant deletion reuses the existing durable storage outbox."""

from django.conf import settings
from django.db import connection
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from common.attachment_cleanup import enqueue_cleanup
from common.models import (
    Address,
    MagicLinkToken,
    Org,
    OrganizationClosure,
    OrganizationInvitation,
    PendingFileDeletion,
    Profile,
    SalesAppointment,
    User,
)
from common.organization_lifecycle import organization_lock


def _delete_unshared_users(users, org_id):
    """Called inside the purge transaction with candidate user rows locked.

    Profiles and Org are auth-bootstrap tables without tenant RLS. Check all
    memberships, including inactive ones, before deleting a global identity.
    Never turn organization deletion into deletion of a platform operator.
    """
    from django.db import transaction

    from common.audit_log import SecurityAuditLog

    for user in users:
        if user.is_superuser or user.is_staff:
            continue
        if Profile.objects.filter(user=user).exists():
            continue
        if Org.objects.filter(owner=user).exists():
            continue
        # These records otherwise retain email/token payloads after User deletion.
        MagicLinkToken.objects.filter(email__iexact=user.email).delete()
        OutstandingToken.objects.filter(user=user).delete()
        SecurityAuditLog.objects.filter(user=user, org__isnull=True).delete()
        if user.profile_image:
            PendingFileDeletion.objects.get_or_create(
                org_id=org_id, name=user.profile_image.name
            )
            transaction.on_commit(enqueue_cleanup)
        user.delete()


def purge_organization(org_id):
    """No force option: both the deployment gate and 30-day deadline must pass.

    The database and file-outbox changes commit together. Storage deletion runs
    later, so a provider outage cannot lose the keys needed for retries.
    """
    if not settings.CRM_ORG_PURGE_ENABLED:
        return False
    from common.identifiers import resolve_identifier

    org_id = resolve_identifier(org_id)
    if PendingFileDeletion.objects.filter(org_id__isnull=True).exists():
        raise ValueError(
            "Drain unattributed legacy file deletions before purging organizations"
        )
    from cases.models import TimeEntry
    from common.audit_log import SecurityAuditLog
    from invoices.models import Estimate, Invoice, RecurringInvoice

    with organization_lock(org_id, exclusive=True):
        receipt = OrganizationClosure.objects.select_for_update().get(org_id=org_id)
        now = timezone.now()
        if receipt.reactivated_at or receipt.deletion_due_at > now:
            return False
        if receipt.data_deleted_at:
            return True
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('app.current_org', %s, true)", [str(org_id)]
                )
        org = Org.objects.select_for_update().get(pk=org_id)
        if not org.closing_at or org.deletion_due_at != receipt.deletion_due_at:
            raise ValueError("Organization closure and deletion ledger disagree")
        user_ids = set(
            Profile.objects.filter(org=org).values_list("user_id", flat=True)
        )
        if org.owner_id:
            user_ids.add(org.owner_id)
        # Lock before removing memberships; concurrent joins cannot commit a new
        # reference to an identity between the final membership check and deletion.
        users = list(
            User.objects.select_for_update().filter(pk__in=user_ids).order_by("pk")
        )
        addresses = list(
            Profile.objects.filter(org=org)
            .exclude(address_id=None)
            .values_list("address_id", flat=True)
        )
        # PROTECT relations are cleared only within the organization being purged.
        # An unexpected protected relation aborts the transaction for investigation.
        SalesAppointment.objects.filter(org=org).delete()
        TimeEntry.objects.filter(org=org).delete()
        Profile.objects.filter(org=org).update(access_role=None)
        OrganizationInvitation.objects.filter(org=org).update(access_role=None)
        for model in (Invoice, Estimate, RecurringInvoice):
            model.objects.filter(org=org).update(account=None)
        # This FK uses SET_NULL; remove its tenant payload instead of orphaning it.
        SecurityAuditLog.objects.filter(org=org).delete()
        org.delete()
        Address.objects.filter(pk__in=addresses, address_users__isnull=True).delete()
        _delete_unshared_users(users, org_id)
        receipt.data_deleted_at = now
        receipt.save(update_fields=["data_deleted_at"])
        return True


def finish_file_deletions():
    for receipt in OrganizationClosure.objects.filter(
        data_deleted_at__isnull=False, files_deleted_at__isnull=True
    ):
        if not PendingFileDeletion.objects.filter(org_id=receipt.org_id).exists():
            receipt.files_deleted_at = timezone.now()
            receipt.save(update_fields=["files_deleted_at"])
