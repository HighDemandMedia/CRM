"""Organization member administration, including the protected creator."""

from rest_framework.exceptions import PermissionDenied


def assert_member_management(actor, target=None, new_role=None):
    if not actor or actor.role != "ADMIN":
        raise PermissionDenied("Only administrators can manage users.")
    if target is not None:
        if target.user.is_superuser or target.is_platform_access:
            raise PermissionDenied(
                "Platform owner access cannot be managed by an organization."
            )
        if target.org_id != actor.org_id:
            raise PermissionDenied("Choose a user in this organization.")
        if target.is_super_admin:
            raise PermissionDenied("The Super Admin cannot be changed or removed.")
        if target.pk == actor.pk:
            raise PermissionDenied("You cannot change your own access.")
    if (
        new_role == "ADMIN" or (target is not None and target.role == "ADMIN")
    ) and not (actor.is_super_admin or actor.user.is_superuser):
        raise PermissionDenied(
            "Only the Super Admin can appoint or manage other administrators."
        )
