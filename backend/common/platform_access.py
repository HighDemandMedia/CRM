"""Explicit platform access, always operating inside one selected tenant."""

from django.db import transaction

from common.models import Org, Profile


def is_platform_owner(user):
    return bool(user and user.is_active and user.is_superuser)


def can_preview(profile):
    return bool(profile and not profile.is_demo and is_platform_owner(profile.user))


def accessible_profiles(user):
    profiles = Profile.objects.filter(
        user=user,
        is_active=True,
        removed_at__isnull=True,
        org__is_active=True,
    ).select_related("org", "user")
    if not is_platform_owner(user):
        profiles = profiles.filter(is_platform_access=False)
    return profiles


def available_organizations(user):
    if is_platform_owner(user):
        return Org.objects.filter(is_active=True).order_by("name")
    return Org.objects.filter(
        pk__in=accessible_profiles(user).values("org_id"),
        is_active=True,
    ).order_by("name")


@transaction.atomic
def select_organization(user, org_id):
    if is_platform_owner(user):
        org = Org.objects.select_for_update().get(pk=org_id, is_active=True)
        profile, created = Profile.objects.get_or_create(
            user=user,
            org=org,
            defaults={"role": "ADMIN", "is_platform_access": True},
        )
        if not created and profile.is_platform_access:
            profile.role = "ADMIN"
            profile.is_active = True
            profile.removed_at = None
            profile.save()
        if not profile.is_active or profile.removed_at:
            raise Profile.DoesNotExist
        return profile
    return accessible_profiles(user).get(org_id=org_id)
