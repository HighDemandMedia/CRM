"""Owner-controlled closure, with reversible access until the export deadline."""

import hashlib
import inspect
from contextlib import contextmanager, nullcontext
from datetime import timedelta
from functools import wraps
from uuid import uuid4

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from common.models import Org, Profile
from common.platform_access import is_platform_owner

READ_ONLY_MESSAGE = (
    "This organization is closing. You can still view and export records."
)
OWNER_REQUIRED_MESSAGE = (
    "Only the organization owner or CRM owner can manage its closure."
)


def can_manage_lifecycle(org, user):
    if is_platform_owner(user):
        return True
    return bool(
        user
        and user.is_active
        and org.owner_id == user.pk
        and Profile.objects.filter(
            org=org, user=user, is_active=True, removed_at__isnull=True
        ).exists()
    )


@contextmanager
def organization_lock(org_id, *, exclusive=False, transactional=True):
    """Drain active writes before closure without serializing ordinary writers.

    HTTP writes use a transaction lock. Jobs use a session lock so successful
    outbox acknowledgements commit independently when a later recipient fails.
    Both lock kinds share PostgreSQL's advisory lock namespace.
    """
    with transaction.atomic() if transactional else nullcontext():
        key = int.from_bytes(
            hashlib.sha256(str(org_id).encode()).digest()[:8], "big", signed=True
        )
        postgres = connection.vendor == "postgresql"
        suffix = "" if exclusive else "_shared"
        if postgres:
            function = f"pg_advisory_{'xact_' if transactional else ''}lock{suffix}"
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT {function}(%s)", [key])
        try:
            yield
        finally:
            if postgres and not transactional:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f"SELECT pg_advisory_unlock{suffix}(%s)", [key])
                except Exception:
                    # Closing a failed connection also releases its session lock.
                    connection.close()
                    raise


@contextmanager
def writable_organization(org_id):
    with organization_lock(org_id):
        if not Org.objects.filter(
            pk=org_id, is_active=True, closing_at__isnull=True
        ).exists():
            raise PermissionDenied(READ_ONLY_MESSAGE)
        yield


def organization_job(function):
    """Drop already-queued tenant work after closure; do not retry a denial."""
    signature = inspect.signature(function)

    @wraps(function)
    def guarded(*args, **kwargs):
        arguments = signature.bind(*args, **kwargs).arguments
        org = arguments.get("org")
        org_id = arguments.get("org_id") or getattr(org, "pk", None)
        if not org_id:
            # Legacy jobs without tenant context cannot safely mutate or send.
            return None
        with organization_lock(org_id, transactional=False):
            if not Org.objects.filter(
                pk=org_id, is_active=True, closing_at__isnull=True
            ).exists():
                return None
            return function(*args, **kwargs)

    return guarded


def lifecycle_payload(org, user=None):
    now = timezone.now()
    owner = can_manage_lifecycle(org, user)
    return {
        "closing_at": org.closing_at,
        "deletion_due_at": org.deletion_due_at,
        "read_only": bool(org.closing_at),
        "can_manage": owner,
        "enabled": owner and settings.CRM_ORG_CLOSURE_ENABLED,
        "purge_enabled": owner and settings.CRM_ORG_PURGE_ENABLED,
        "can_reactivate": bool(
            owner
            and org.closing_at
            and org.deletion_due_at
            and now < org.deletion_due_at
        ),
    }


def change_lifecycle(org_id, actor, action, *, confirmation=None):
    from common.models import GoogleConnection, OrganizationInvitation, User
    from common.organization_lifecycle_models import (
        OrganizationClosure,
        OrganizationLifecycleEvent,
    )
    from webforms.models import WebFormSubmission

    # Re-read user privileges: stale requests must not retain revoked ownership.
    actor = User.objects.filter(pk=getattr(actor, "pk", None), is_active=True).first()
    if actor is None:
        raise PermissionDenied(OWNER_REQUIRED_MESSAGE)
    if action == "close" and not settings.CRM_ORG_CLOSURE_ENABLED:
        raise ValidationError("Organization closure is not enabled on this deployment.")
    if action not in ("close", "reactivate"):
        raise ValidationError("Choose close or reactivate.")
    with organization_lock(org_id, exclusive=True):
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('app.current_org', %s, true)", [str(org_id)]
                )
        org = Org.objects.select_for_update().get(pk=org_id, is_active=True)
        if not can_manage_lifecycle(org, actor):
            raise PermissionDenied(OWNER_REQUIRED_MESSAGE)
        # Validate against the locked, current name, including concurrent renames.
        if confirmation is not None and confirmation != org.name:
            raise ValidationError(
                {"confirmation": "Enter the organization name to confirm."}
            )
        now = timezone.now()
        if action == "close":
            if org.closing_at:
                return org  # Repeated clicks must never extend the deadline.
            org.closing_at = now
            org.deletion_due_at = now + timedelta(days=30)
            OrganizationClosure.objects.update_or_create(
                org_id=org.pk,
                defaults={
                    "requested_at": now,
                    "deletion_due_at": org.deletion_due_at,
                    "reactivated_at": None,
                    "data_deleted_at": None,
                    "files_deleted_at": None,
                },
            )
            # Clear credentials, not Google-owned mail/events. In-flight work has
            # finished before the exclusive lock; a stale OAuth callback cannot reconnect.
            GoogleConnection.objects.filter(org=org).update(
                status="disconnected",
                encrypted_refresh_token="",
                oauth_state_hash="",
                encrypted_verifier="",
                oauth_started_at=None,
                sync_started_at=None,
                generation=uuid4(),
                error="",
            )
            OrganizationInvitation.objects.filter(
                org=org, accepted_at__isnull=True, revoked_at__isnull=True
            ).update(revoked_at=now)
            # Cancel unsent outbox notifications; reactivation must not send old submissions.
            WebFormSubmission.objects.filter(
                org=org, email_completed_at__isnull=True
            ).update(email_completed_at=now)
            WebFormSubmission.objects.filter(
                org=org,
                confirmation_requested=True,
                confirmation_completed_at__isnull=True,
            ).update(
                confirmation_completed_at=now,
                confirmation_claim_id=None,
                confirmation_claimed_at=None,
            )
        else:
            if not org.closing_at:
                return org
            if not org.deletion_due_at or now >= org.deletion_due_at:
                raise ValidationError(
                    "The 30-day period has ended. This organization cannot be reactivated and its data cannot be recovered."
                )
            OrganizationClosure.objects.filter(
                org_id=org.pk, data_deleted_at__isnull=True
            ).update(reactivated_at=now)
            org.closing_at = None
            org.deletion_due_at = None
        org.save(update_fields=["closing_at", "deletion_due_at"])
        OrganizationLifecycleEvent.objects.create(
            org_id=org.pk, actor_id=actor.pk, action=action
        )
        return org


def invitation_write(function):
    """Invitation acceptance is org-free authentication, so gate its token's tenant."""

    @wraps(function)
    def guarded(self, request, *args, **kwargs):
        from common.models import OrganizationInvitation

        raw = request.data.get("invitation") or request.data.get("token")
        if not isinstance(raw, str):
            return function(self, request, *args, **kwargs)
        org_id = (
            OrganizationInvitation.objects.filter(
                token_hash=hashlib.sha256(raw.encode()).hexdigest(), org__is_active=True
            )
            .values_list("org_id", flat=True)
            .first()
        )
        if org_id is None:
            return function(self, request, *args, **kwargs)
        with writable_organization(org_id):
            return function(self, request, *args, **kwargs)

    return guarded
