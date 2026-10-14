"""Versioned, explicit acceptance at the invitation boundary.

An empty version keeps enforcement off until the reviewed documents are public.
The server, not a posted URL or version, determines what a user can accept.
"""

from django.conf import settings
from rest_framework.exceptions import ValidationError

from common.models import LegalAcceptance


def legal_requirements(invitation):
    return {
        "version": settings.CRM_LEGAL_VERSION,
        "organization_authority_required": invitation.grants_ownership,
    }


def validate_legal_acceptance(data, invitation):
    version = settings.CRM_LEGAL_VERSION
    if not version:
        return None
    if data.get("legal_version") != version:
        raise ValidationError(
            {
                "error": "The terms have changed. Reload this page and review them before continuing."
            }
        )
    if data.get("accept_terms") is not True:
        raise ValidationError({"error": "Accept the CRM Terms of Service to continue."})
    if invitation.grants_ownership and data.get("organization_authority") is not True:
        raise ValidationError(
            {"error": "Confirm that you can accept these terms for your organization."}
        )
    locale = data.get("legal_locale")
    if locale not in ("en", "es"):
        raise ValidationError(
            {"error": "Select English or Spanish and review the terms."}
        )
    return {
        "version": version,
        "locale": locale,
        "on_behalf_of_organization": invitation.grants_ownership,
    }


def record_legal_acceptance(user, invitation, acceptance):
    if acceptance:
        # Independent of invitations: resending/reusing an invitation must not
        # overwrite prior evidence. No passwords, tokens, IPs or browser IDs.
        LegalAcceptance.objects.create(user=user, org=invitation.org, **acceptance)
