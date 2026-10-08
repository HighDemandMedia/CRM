"""Explicit Manager delegation, independent of record visibility scopes."""

from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import SAFE_METHODS, BasePermission

from common.permissions import is_org_admin

SETTINGS_SECTIONS = (
    "organization",
    "properties",
    "creation_forms",
    "pipelines",
    "tags",
    "forms",
)
SETTINGS_LEVELS = ("none", "read", "manage")


def validate_settings_access(value):
    if not isinstance(value, dict) or set(value) - set(SETTINGS_SECTIONS):
        raise ValidationError("Choose supported Settings sections.")
    if any(level not in SETTINGS_LEVELS for level in value.values()):
        raise ValidationError("Choose No access, Read only or Manage.")
    return {key: value.get(key, "none") for key in SETTINGS_SECTIONS}


def settings_access(profile):
    denied = dict.fromkeys(SETTINGS_SECTIONS, "none")
    if not profile or not profile.is_active or profile.removed_at:
        return denied
    if is_org_admin(profile):
        return dict.fromkeys(SETTINGS_SECTIONS, "manage")
    role = profile.access_role
    if not role or role.org_id != profile.org_id or role.name != "Manager":
        return denied
    grants = role.settings_access
    if not isinstance(grants, dict):
        return denied
    return {
        key: grants.get(key) if grants.get(key) in SETTINGS_LEVELS else "none"
        for key in SETTINGS_SECTIONS
    }


def can_access_settings(profile, section, manage=False):
    level = settings_access(profile).get(section, "none")
    return level == "manage" if manage else level in ("read", "manage")


def require_settings(profile, section, manage=False):
    if not can_access_settings(profile, section, manage):
        raise PermissionDenied("You do not have permission to access these settings.")


class HasSettingsAccess(BasePermission):
    message = "You do not have permission to access these settings."

    def has_permission(self, request, view):
        return can_access_settings(
            getattr(request, "profile", None),
            view.settings_section,
            manage=request.method not in SAFE_METHODS,
        )
