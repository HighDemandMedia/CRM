"""Atomic invitation enrollment shared by password and verified Google access."""

import hashlib

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from common.invitations import accept_ownership
from common.legal import record_legal_acceptance, validate_legal_acceptance
from common.models import OrganizationInvitation, Profile, User
from common.rbac import ensure_default_roles
from common.rls.context import org_context


@transaction.atomic
def register_invited_user(
    *, token, email, name, password, legal_data, allow_existing=False
):
    if not isinstance(token, str) or not 20 <= len(token) <= 128:
        raise ValidationError(
            {"error": "Invitation is invalid, expired, or belongs to another email."}
        )
    invitation = (
        OrganizationInvitation.objects.select_for_update()
        .select_related("org")
        .filter(
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            email__iexact=email,
            accepted_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
            org__is_active=True,
            org__closing_at__isnull=True,
        )
        .first()
    )
    if invitation is None:
        raise ValidationError(
            {"error": "Invitation is invalid, expired, or belongs to another email."}
        )
    acceptance = validate_legal_acceptance(legal_data, invitation)
    user = User.objects.select_for_update().filter(email__iexact=email).first()
    if user is not None:
        if not allow_existing:
            raise ValidationError(
                {
                    "error": "This email cannot be registered. Sign in or use email recovery."
                }
            )
        if not user.is_active:
            raise PermissionDenied(
                {"error": "User account is disabled", "code": "account_disabled"}
            )
    else:
        # None produces an unusable password: Google never shares its password.
        user = User.objects.create_user(email.lower(), password, name=name)
    complete_invited_membership(invitation, user, acceptance)
    return user, invitation


def complete_invited_membership(invitation, user, acceptance):
    """Called with the invitation locked inside the caller's transaction."""
    with org_context(invitation.org_id):
        if Profile.objects.filter(
            org=invitation.org, user=user, removed_at__isnull=True
        ).exists():
            raise ValidationError(
                {
                    "error": "Membership already exists. Ask an admin if access is inactive."
                }
            )
        Profile.objects.update_or_create(
            org=invitation.org,
            user=user,
            defaults={
                "role": invitation.role,
                "access_role": (
                    invitation.access_role or ensure_default_roles(invitation.org)[0]
                )
                if invitation.role == "USER"
                else None,
                "is_active": True,
                "removed_at": None,
                "date_of_joining": timezone.localdate(),
                "setup_step": Profile.SetupStep.PROFILE_ORGANIZATION
                if invitation.grants_ownership
                else Profile.SetupStep.PROFILE,
            },
        )
        accept_ownership(invitation, user)
        record_legal_acceptance(user, invitation, acceptance)
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["accepted_at"])
