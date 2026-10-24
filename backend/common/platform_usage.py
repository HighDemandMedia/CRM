"""Bounded, cached counters for the platform owner; never bypass tenant RLS."""

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.models import CharField, Count, Value
from django.utils import timezone

from accounts.models import Account
from cases.models import Case
from common.models import Attachments, Profile, SalesAppointment
from common.rls.context import org_context
from common.usage_limits import LIMIT_KEYS, seat_emails
from contacts.models import Contact
from opportunity.models import Opportunity
from tasks.models import Task

CACHE_SECONDS = 60
RECORD_MODELS = {
    "contacts": Contact,
    "companies": Account,
    "deals": Opportunity,
    "tasks": Task,
    "tickets": Case,
    "appointments": SalesAppointment,
    "attachments": Attachments,
}


def organization_usage(org):
    # One minute cache per tenant bounds repeated COUNT scans. No record content,
    # email addresses or credentials are collected or returned.
    key = f"platform-usage:v2:org:{org.pk}"
    result = cache.get(key)
    if result is None:
        with org_context(org.pk):
            queries = {
                key: model.objects.filter(org_id=org.pk)
                for key, model in RECORD_MODELS.items()
            }
            queries["users"] = Profile.objects.filter(
                org=org,
                is_active=True,
                removed_at__isnull=True,
                is_platform_access=False,
                user__is_active=True,
            )
            # UNION keeps each table's count independent (no multiplying joins)
            # while requiring only one database round trip per organization.
            counters = [
                queryset.order_by()
                .annotate(metric=Value(key, output_field=CharField()))
                .values("metric")
                .annotate(total=Count("pk"))
                .values_list("metric", "total")
                for key, queryset in queries.items()
            ]
            result = dict.fromkeys(queries, 0)
            result.update(
                dict(counters[0].union(*counters[1:], all=True).order_by("metric"))
            )
        result["measured_at"] = timezone.now().isoformat()
        result["reserved_users"] = len(seat_emails(org.pk))
        cache.set(key, result, CACHE_SECONDS)
    return {
        **result,
        "limits": {key: org.usage_limits.get(key) for key in LIMIT_KEYS},
        "id": str(org.pk),
        "name": org.name,
        "status": "Closing"
        if org.closing_at
        else "Active"
        if org.is_active
        else "Inactive",
    }


def database_capacity(used_bytes):
    """Configured allocation, not filesystem capacity or a database-enforced quota."""
    configured = settings.CRM_DATABASE_CAPACITY_BYTES
    total = configured if configured > 0 else None
    remaining = (
        max(0, total - used_bytes)
        if total is not None and used_bytes is not None
        else None
    )
    ratio = used_bytes / total if total and used_bytes is not None else None
    # These are planning thresholds, not provider-enforced limits. Database size
    # excludes WAL/logs, so Render's disk metric remains the authoritative check.
    status = "unknown"
    if ratio is not None:
        status = (
            "critical"
            if ratio >= 0.9
            else "expand"
            if ratio >= 0.8
            else "plan"
            if ratio >= 0.7
            else "normal"
        )
    return {
        "total_bytes": total,
        "remaining_estimated_bytes": remaining,
        "used_percent": round(ratio * 100, 1) if ratio is not None else None,
        "capacity_status": status,
    }


def database_usage():
    result = {"bytes": None, "measured_at": None}
    if connection.vendor == "postgresql":
        key = "platform-usage:v1:database"
        result = cache.get(key)
        if result is None:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_database_size(current_database())")
                size = cursor.fetchone()[0]
            result = {"bytes": size, "measured_at": timezone.now().isoformat()}
            cache.set(key, result, CACHE_SECONDS)
    return {
        **result,
        **database_capacity(result["bytes"]),
        "environment": "Local database" if settings.IS_DEV_ENV else "Hosted database",
    }
