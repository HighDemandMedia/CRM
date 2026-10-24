"""Organization quotas, independent of the requesting member's record visibility.

The organization row serializes capacity checks and writes, including limit edits.
Counts used for enforcement are live; dashboard caches must never authorize writes.
"""

from contextlib import contextmanager

from django.apps import apps
from django.core.cache import cache
from django.db import models, transaction
from django.db.models.functions import Lower
from django.utils import timezone
from rest_framework.exceptions import APIException

RECORD_RESOURCES = {
    "contacts.contact": "contacts",
    "accounts.account": "companies",
    "opportunity.opportunity": "deals",
    "tasks.task": "tasks",
    "cases.case": "tickets",
    "common.salesappointment": "appointments",
}
LIMIT_KEYS = ("users", *RECORD_RESOURCES.values())


def default_organization_limits():
    """Initial allowance for new accounts; existing quotas remain owner-managed."""
    return {"users": 5, "contacts": 2500, "companies": 500, "deals": 500}


SEAT_MODELS = {"common.profile", "common.organizationinvitation"}
SEAT_FIELDS = {
    "common.profile": {"is_active", "removed_at", "is_platform_access", "user_id"},
    "common.organizationinvitation": {
        "email",
        "accepted_at",
        "revoked_at",
        "expires_at",
    },
}


class OrganizationLimitReached(APIException):
    status_code = 409
    default_code = "organization_limit_reached"

    def __init__(self, resource):
        super().__init__(
            {
                "error": f"This organization has reached its {resource} limit. Contact High Demand Media to increase it.",
                "code": self.default_code,
                "resource": resource,
            }
        )


def raw_rows(model, org_id, using="default"):
    # Bypass member-level managers, but retain PostgreSQL tenant RLS.
    return models.QuerySet(model=model, using=using).filter(org_id=org_id)


def seat_emails(org_id, using="default"):
    profiles = raw_rows(apps.get_model("common.Profile"), org_id, using).filter(
        is_active=True, removed_at__isnull=True, is_platform_access=False
    )
    invitations = raw_rows(
        apps.get_model("common.OrganizationInvitation"), org_id, using
    ).filter(
        accepted_at__isnull=True, revoked_at__isnull=True, expires_at__gt=timezone.now()
    )
    from common.rls.context import org_context

    with org_context(org_id):
        return set(
            profiles.order_by()
            .annotate(seat=Lower("user__email"))
            .values_list("seat", flat=True)
            .union(
                invitations.order_by()
                .annotate(seat=Lower("email"))
                .values_list("seat", flat=True)
            )
            .order_by()
        )


def resource_count(org_id, resource, using="default"):
    if resource == "users":
        return len(seat_emails(org_id, using))
    label = next(key for key, value in RECORD_RESOURCES.items() if value == resource)
    rows = raw_rows(apps.get_model(label), org_id, using)
    if resource == "contacts":
        rows = rows.filter(merged_at__isnull=True)
    from common.rls.context import org_context

    with org_context(org_id):
        return rows.count()


def invalidate_usage(org_id):
    cache.delete(f"platform-usage:v2:org:{org_id}")


@contextmanager
def locked_quota(org_id, using="default"):
    with transaction.atomic(using=using):
        org = (
            apps.get_model("common.Org")
            .objects.using(using)
            .select_for_update()
            .get(pk=org_id)
        )
        yield org


@contextmanager
def guard_save(instance, using="default", update_fields=None):
    label = instance._meta.label_lower
    resource = "users" if label in SEAT_MODELS else RECORD_RESOURCES.get(label)
    if not resource or not instance.org_id:
        yield
        return
    written_fields = None
    if update_fields is not None:
        written_fields = {
            instance._meta.get_field(name).attname for name in update_fields
        }
    if (
        not instance._state.adding
        and resource == "users"
        and written_fields is not None
        and not written_fields.intersection(SEAT_FIELDS[label])
    ):
        # Profile preferences do not consume a seat. In particular, avoid
        # taking an organization lock after the profile has already been locked.
        yield
        return
    # Ordinary edits neither consume capacity nor need to lock the organization.
    if not instance._state.adding and resource != "users":
        if resource != "contacts" or (
            update_fields is not None and "merged_at" not in update_fields
        ):
            yield
            return
        previous = (
            raw_rows(type(instance), instance.org_id, using)
            .filter(pk=instance.pk)
            .first()
        )
        if (
            previous is None
            or previous.merged_at is None
            or instance.merged_at is not None
        ):
            yield
            return
    with locked_quota(instance.org_id, using) as org:
        maximum = org.usage_limits.get(resource)
        if maximum is not None:
            candidate = instance
            if (
                resource == "users"
                and not instance._state.adding
                and written_fields is not None
            ):
                candidate = raw_rows(type(instance), instance.org_id, using).get(
                    pk=instance.pk
                )
                for field in SEAT_FIELDS[label].intersection(written_fields):
                    setattr(candidate, field, getattr(instance, field))
            grows = True
            if label == "common.profile":
                grows = (
                    candidate.is_active
                    and not candidate.removed_at
                    and not candidate.is_platform_access
                )
                email = candidate.user.email.lower()
            elif label == "common.organizationinvitation":
                grows = (
                    not candidate.accepted_at
                    and not candidate.revoked_at
                    and candidate.expires_at > timezone.now()
                )
                email = candidate.email.lower()
            elif resource == "contacts":
                grows = instance.merged_at is None
            if resource == "users" and grows:
                # Acceptance exchanges a reservation for a membership, and a
                # resend keeps the same reservation even after a lowered limit.
                grows = email not in seat_emails(org.pk, using)
            if grows and resource_count(org.pk, resource, using) >= maximum:
                raise OrganizationLimitReached(resource)
        yield
        transaction.on_commit(lambda: invalidate_usage(org.pk), using=using)


class QuotaModelMixin(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        using = kwargs.get("using") or self._state.db or "default"
        with guard_save(self, using, kwargs.get("update_fields")):
            return super().save(*args, **kwargs)


class QuotaQuerySet(models.QuerySet):
    def bulk_create(self, objs, **kwargs):
        objs = list(objs)
        if self.model._meta.label_lower not in {*RECORD_RESOURCES, *SEAT_MODELS}:
            return super().bulk_create(objs, **kwargs)
        if kwargs.get("ignore_conflicts") or kwargs.get("update_conflicts"):
            raise ValueError(
                "Quota-managed records require explicit create or update operations."
            )
        with transaction.atomic(using=self.db):
            for obj in sorted(objs, key=lambda row: str(row.org_id)):
                obj.save(force_insert=True, using=self.db)
        return objs

    def update(self, **kwargs):
        label = self.model._meta.label_lower
        resource = "users" if label in SEAT_MODELS else RECORD_RESOURCES.get(label)
        if not resource:
            return super().update(**kwargs)
        if "org" in kwargs or "org_id" in kwargs:
            raise ValueError(
                "Move records between organizations through an explicit transfer workflow."
            )
        fields = (
            {
                "is_active",
                "removed_at",
                "is_platform_access",
                "user",
                "user_id",
                "email",
                "accepted_at",
                "revoked_at",
                "expires_at",
            }
            if resource == "users"
            else {"merged_at"}
        )
        if not fields.intersection(kwargs):
            return super().update(**kwargs)
        from contextlib import ExitStack

        # Bulk status/restoration updates bypass model.save. Lock every affected
        # organization in a stable order and roll back a capacity-increasing write.
        with transaction.atomic(using=self.db), ExitStack() as stack:
            org_ids = sorted(set(self.values_list("org_id", flat=True)), key=str)
            limits = []
            for org_id in org_ids:
                org = stack.enter_context(locked_quota(org_id, self.db))
                maximum = org.usage_limits.get(resource)
                if maximum is not None:
                    limits.append(
                        (org, maximum, resource_count(org.pk, resource, self.db))
                    )
            result = super().update(**kwargs)
            for org, maximum, before in limits:
                after = resource_count(org.pk, resource, self.db)
                if after > before and after > maximum:
                    raise OrganizationLimitReached(resource)
            for org_id in org_ids:
                transaction.on_commit(
                    lambda pk=org_id: invalidate_usage(pk), using=self.db
                )
            return result


QuotaManager = models.Manager.from_queryset(QuotaQuerySet)
