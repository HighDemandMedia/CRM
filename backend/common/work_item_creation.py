"""Shared ownership and association rules for manual task/ticket creation."""

from rest_framework.exceptions import ValidationError

from common.models import Profile
from common.permissions import is_org_admin
from common.validators import payload_id_list
from contacts.models import Contact


def chooses_assignee(profile):
    role = profile.access_role
    return is_org_admin(profile) or bool(
        role and role.org_id == profile.org_id and role.name == "Manager"
    )


def prepare_creation(request):
    """Normalize ownership before saving; never silently discard invalid relations."""
    profile = request.profile
    if not isinstance(request.data, dict):
        raise ValidationError("Send a record object.")
    data = request.data.copy()
    owners = payload_id_list(data.get("assigned_to"), "assigned_to")
    if chooses_assignee(profile):
        if not owners:
            raise ValidationError({"assigned_to": "Choose an assignee."})
    else:
        if owners and {str(pk) for pk in owners} != {str(profile.pk)}:
            raise ValidationError({"assigned_to": "New records are assigned to you."})
        owners = [str(profile.pk)]
    allowed = Profile.objects.filter(
        org_id=profile.org_id, is_active=True, pk__in=owners
    )
    if {str(pk) for pk in owners} != {
        str(pk) for pk in allowed.values_list("pk", flat=True)
    }:
        raise ValidationError(
            {"assigned_to": "Choose an active user in this organization."}
        )
    data["assigned_to"] = owners
    # Company foreign keys are validated by each serializer. M2M contacts are
    # written separately by the views, so validate all IDs before any write.
    ids = payload_id_list(data.get("contacts"), "contacts")
    allowed_ids = Contact.objects.filter(org_id=profile.org_id, pk__in=ids).values_list(
        "pk", flat=True
    )
    if {str(pk) for pk in ids} != {str(pk) for pk in allowed_ids}:
        raise ValidationError(
            {"contacts": "Choose an accessible record in this organization."}
        )
    return data
