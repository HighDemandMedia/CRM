"""Permission-scoped period reports. Current record state, never historical snapshots."""

import csv
from datetime import datetime, time, timedelta
from io import StringIO
from zoneinfo import ZoneInfo

from django.db import models
from django.db.models import Case as SQLCase
from django.db.models import Count, Q, Sum, Value, When
from django.db.models.functions import Coalesce, NullIf, TruncDay, TruncMonth, TruncWeek
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account
from cases.models import Case
from common.last_activity import with_last_activity
from common.models import Profile, SalesAppointment
from common.permissions import HasOrgContext, is_org_admin
from common.pipeline_settings import stages_for
from common.rbac import calendar_scoped, configured, require, scope_for, scoped
from contacts.models import Contact
from opportunity.models import Opportunity
from tasks.models import Task

# Only these server-defined fields can become SQL expressions.
CONFIG = {
    "contacts": (
        Contact,
        "Contacts",
        "/contacts",
        "stage",
        {
            "created_at": "Created date",
            "last_activity_at": "Last activity",
            "stage_entered_at": "Last stage change",
            "appointment_at": "Appointment",
        },
        {"stage": "Stage", "source": "Source", "language": "Language"},
    ),
    "companies": (
        Account,
        "Companies",
        "/accounts",
        "stage",
        {
            "created_at": "Created date",
            "last_activity_at": "Last activity",
            "stage_entered_at": "Last stage change",
            "appointment_at": "Appointment",
        },
        {"stage": "Stage", "source": "Source", "industry": "Industry"},
    ),
    "deals": (
        Opportunity,
        "Deals",
        "/pipeline",
        "stage",
        {
            "created_at": "Created date",
            "last_activity_at": "Last activity",
            "stage_changed_at": "Last stage change",
            "closed_on": "Expected close date",
        },
        {"stage": "Stage", "lead_source": "Source", "priority": "Priority"},
    ),
    "tasks": (
        Task,
        "Tasks",
        "/tasks",
        "status",
        {
            "created_at": "Created date",
            "last_activity_at": "Last activity",
            "due_date": "Due date",
        },
        {"status": "Stage", "priority": "Priority"},
    ),
    "tickets": (
        Case,
        "Tickets",
        "/tickets",
        "status",
        {
            "created_at": "Created date",
            "last_activity_at": "Last activity",
            "due_at": "Due date",
            "resolved_at": "Resolved date",
            "closed_on": "Closed date",
            "first_response_at": "First response",
        },
        {
            "status": "Stage",
            "priority": "Priority",
            "source": "Source",
            "category": "Category",
        },
    ),
    "events": (
        SalesAppointment,
        "Events",
        "/calendar",
        "event_status",
        {
            "starts_at": "Event start",
            "created_at": "Scheduled date",
            "cancelled_at": "Cancelled date",
        },
        {"event_status": "Status"},
    ),
}
PAGE_SIZE = 20


def available(profile, key):
    return (
        not configured(profile)
        or scope_for(profile, "calendar" if key == "events" else key) != "none"
    )


def base_records(profile, key):
    model = CONFIG[key][0]
    # Build one outer row per record; role/owner M2M joins stay in subqueries.
    qs = model._base_manager.filter(org_id=profile.org_id)
    if key == "events":
        qs = calendar_scoped(
            qs,
            profile,
            limit=scope_for(profile, "reports", "view")
            if configured(profile)
            else None,
        )
        return qs.annotate(
            event_status=SQLCase(
                When(cancelled_at__isnull=False, then=Value("cancelled")),
                default=Value("scheduled"),
                output_field=models.CharField(),
            )
        )
    if key in ("contacts", "tickets"):
        qs = qs.filter(merged_at__isnull=True)
    if configured(profile):
        qs = qs.filter(
            pk__in=scoped(
                qs, profile, limit=scope_for(profile, "reports", "view")
            ).values("pk")
        )
    elif not is_org_admin(profile):
        qs = qs.filter(
            pk__in=qs.filter(
                Q(assigned_to=profile) | Q(created_by=profile.user)
            ).values("pk")
        )
    return qs


def window(qs, field, start, end, tz):
    if field == "last_activity_at":
        qs = with_last_activity(qs)
        is_datetime = True
    else:
        is_datetime = isinstance(qs.model._meta.get_field(field), models.DateTimeField)
    if is_datetime:
        start = datetime.combine(start, time.min, tzinfo=tz)
        end = datetime.combine(end + timedelta(days=1), time.min, tzinfo=tz)
        return qs.filter(**{field + "__gte": start, field + "__lt": end})
    return qs.filter(**{field + "__gte": start, field + "__lte": end})


def money_totals(qs, currency):
    rows = (
        qs.annotate(
            money_currency=Coalesce(NullIf("currency", Value("")), Value(currency))
        )
        .order_by()
        .values("money_currency")
        .annotate(amount=Sum("amount"), count=Count("pk"))
    )
    return [
        {
            "currency": r["money_currency"],
            "amount": str(r["amount"] or 0),
            "count": r["count"],
        }
        for r in rows.order_by("money_currency")
    ]


def csv_safe(value):
    text = str(value if value is not None else "")
    return (
        "'" + text
        if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r"))
        else text
    )


class CRMReportView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        profile = request.profile
        require(profile, "reports", "view")
        org = profile.org
        params = request.query_params
        objects = [
            {
                "key": key,
                "label": cfg[1],
                "dates": [{"key": k, "label": v} for k, v in cfg[4].items()],
                "groups": [{"key": k, "label": v} for k, v in cfg[5].items()],
            }
            for key, cfg in CONFIG.items()
            if available(profile, key)
        ]
        if not objects:
            raise PermissionDenied("Your permission set has no reportable objects.")
        key = params.get("object") or objects[0]["key"]
        if key not in CONFIG:
            raise ValidationError("Choose a report object.")
        if not available(profile, key):
            raise PermissionDenied("Your role cannot view this object.")
        model, label, path, state_field, dates, groups = CONFIG[key]
        field = params.get("date_field") or next(iter(dates))
        group = params.get("group_by") or next(iter(groups))
        if field not in dates or group not in groups:
            raise ValidationError(
                "Choose an available date and breakdown for this object."
            )
        tz = ZoneInfo(org.timezone or "UTC")
        today = timezone.localdate(timezone.now(), tz)
        date_parser = serializers.DateField()
        start = date_parser.run_validation(
            params.get("start", (today - timedelta(days=29)).isoformat())
        )
        end = date_parser.run_validation(params.get("end", today.isoformat()))
        days = (end - start).days + 1
        if not 1 <= days <= 3660 or start.year < 1901 or end.year > 9998:
            raise ValidationError(
                "Choose a valid date range of up to 10 years, starting after 1900."
            )
        bucket = params.get("interval", "auto")
        if bucket not in ("auto", "day", "week", "month"):
            raise ValidationError("Choose day, week or month.")
        if bucket == "auto":
            bucket = "day" if days <= 62 else "week" if days <= 366 else "month"
        if (bucket == "day" and days > 366) or (bucket == "week" and days > 2562):
            raise ValidationError(
                "Use a larger time interval for this range (maximum 366 points)."
            )
        page = serializers.IntegerField(min_value=1, max_value=1000000).run_validation(
            params.get("page", 1)
        )
        qs = base_records(profile, key)
        if key == "events":
            states = [
                {"key": "scheduled", "label": "Scheduled"},
                {"key": "cancelled", "label": "Cancelled"},
            ]
            owners = Profile.objects.filter(
                org=org, pk__in=qs.values("host_id")
            ).select_related("user")
        else:
            states = [
                {"key": s["key"], "label": s["label"]}
                for s in stages_for(org, model.__name__)
            ]
            owners = Profile.objects.filter(
                org=org, pk__in=qs.values("assigned_to")
            ).select_related("user")
        owners = [
            {"id": str(p.pk), "name": p.user.name or p.user.email}
            for p in owners.order_by("user__name", "pk")
        ]
        owner = params.get("owner", "")
        if owner:
            owner = str(serializers.UUIDField().run_validation(owner))
            if owner not in {p["id"] for p in owners}:
                raise ValidationError("Choose an owner available in this report.")
            qs = (
                qs.filter(host_id=owner)
                if key == "events"
                else qs.filter(pk__in=qs.filter(assigned_to=owner).values("pk"))
            )
        state = params.get("stage", "")
        if state:
            if state not in {s["key"] for s in states}:
                raise ValidationError("Choose an available stage or status.")
            qs = qs.filter(**{state_field: state})
        object_module = "calendar" if key == "events" else key
        export_allowed = is_org_admin(profile) or (
            configured(profile)
            and scope_for(profile, "reports", "export") != "none"
            and scope_for(profile, "reports", "export")
            == scope_for(profile, "reports", "view")
            and scope_for(profile, object_module, "export")
            == scope_for(profile, object_module, "view")
            and scope_for(profile, object_module, "export") != "none"
        )
        if params.get("download") == "csv" and not export_allowed:
            raise PermissionDenied(
                "Export permission must cover the records included in this report."
            )
        current = window(qs, field, start, end, tz)
        previous_end = start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=days - 1)
        previous = window(qs, field, previous_start, previous_end, tz)
        total, previous_total = current.count(), previous.count()
        state_labels = {s["key"]: s["label"] for s in states}
        group_labels = (
            state_labels
            if group == state_field
            else dict(model._meta.get_field(group).choices or [])
        )
        breakdown = [
            {
                "key": r[group] or "",
                "label": group_labels.get(r[group], r[group]) or "Not set",
                "count": r["count"],
            }
            for r in current.order_by()
            .values(group)
            .annotate(count=Count("pk"))
            .order_by("-count", group)
        ]
        is_datetime = field == "last_activity_at" or isinstance(
            model._meta.get_field(field), models.DateTimeField
        )
        truncate = {"day": TruncDay, "week": TruncWeek, "month": TruncMonth}[bucket]
        series_rows = (
            current.annotate(
                period=truncate(field, **({"tzinfo": tz} if is_datetime else {}))
            )
            .order_by()
            .values("period")
            .annotate(count=Count("pk"))
            .order_by("period")
        )
        series_map = {
            (
                r["period"].date() if isinstance(r["period"], datetime) else r["period"]
            ): r["count"]
            for r in series_rows
        }
        cursor = (
            start.replace(day=1)
            if bucket == "month"
            else start - timedelta(days=start.weekday())
            if bucket == "week"
            else start
        )
        series = []
        while cursor <= end:
            series.append(
                {"date": cursor.isoformat(), "count": series_map.get(cursor, 0)}
            )
            cursor = (
                (
                    cursor.replace(year=cursor.year + 1, month=1)
                    if cursor.month == 12
                    else cursor.replace(month=cursor.month + 1)
                )
                if bucket == "month"
                else cursor + timedelta(days=7 if bucket == "week" else 1)
            )
        status_counts = {
            state_labels.get(r[state_field], r[state_field]) or "Not set": r["count"]
            for r in current.order_by().values(state_field).annotate(count=Count("pk"))
        }
        # Never sum different currencies or call a current deal amount collected revenue.
        amounts = money_totals(current, org.default_currency) if key == "deals" else []
        previous_amounts = (
            money_totals(previous, org.default_currency) if key == "deals" else []
        )
        won_amounts = (
            money_totals(current.filter(stage="CLOSED_WON"), org.default_currency)
            if key == "deals"
            else []
        )
        result = {
            "objects": objects,
            "object": key,
            "label": label,
            "date_field": field,
            "date_label": dates[field],
            "group_by": group,
            "group_label": groups[group],
            "interval": bucket,
            "start": start,
            "end": end,
            "today": today,
            "timezone": str(tz),
            "previous_start": previous_start,
            "previous_end": previous_end,
            "owner": owner,
            "owners": owners,
            "stage": state,
            "stages": states,
            "can_export": export_allowed,
            "summary": {
                "count": total,
                "previous_count": previous_total,
                "change_percent": round(
                    (total - previous_total) * 100 / previous_total, 1
                )
                if previous_total
                else None,
                "amounts": amounts,
                "previous_amounts": previous_amounts,
                "won_amounts": won_amounts,
                "statuses": status_counts,
            },
            "breakdown": breakdown,
            "series": series,
            "page": page,
            "page_size": PAGE_SIZE,
            "pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE),
        }
        if params.get("download") == "csv":
            output = StringIO()
            writer = csv.writer(output)

            def row(*values):
                writer.writerow([csv_safe(v) for v in values])

            row("Report", label)
            row("Date basis", dates[field])
            row("Start", start)
            row("End", end)
            row("Timezone", tz)
            row(
                "Owner",
                next(
                    (p["name"] for p in owners if p["id"] == owner),
                    "All accessible owners",
                ),
            )
            row("Stage", state_labels.get(state, "All stages"))
            row("State", "Current record values, not a historical snapshot")
            row("Records", total)
            row("Previous period records", previous_total)
            row("Previous start", previous_start)
            row("Previous end", previous_end)
            for a in amounts:
                row("Deal value", a["currency"], a["amount"])
            for a in won_amounts:
                row("Currently won deal value", a["currency"], a["amount"])
            row()
            row(groups[group], "Records")
            for item in breakdown:
                row(item["label"], item["count"])
            row()
            row(bucket.title() + " beginning", "Records")
            for item in series:
                row(item["date"], item["count"])
            response = HttpResponse(
                "\ufeff" + output.getvalue(), content_type="text/csv; charset=utf-8"
            )
            response["Content-Disposition"] = (
                f'attachment; filename="{key}-report-{start}-{end}.csv"'
            )
            response["Cache-Control"] = "private, no-store"
            return response
        if page > result["pages"]:
            raise ValidationError(
                "This report page no longer exists. Return to the first page."
            )
        rows = current.order_by("-" + field, "pk")[
            (page - 1) * PAGE_SIZE : page * PAGE_SIZE
        ]
        rows = (
            rows.select_related("host__user")
            if key == "events"
            else rows.prefetch_related("assigned_to__user")
        )
        result["records"] = [
            {
                "id": str(record.pk),
                "name": record.title if key in ("tasks", "events") else record.name,
                "url": f"{path}?date={timezone.localtime(record.starts_at, tz).date()}"
                if key == "events"
                else f"{path}/{record.pk}",
                "date": getattr(record, field),
                "state": state_labels.get(
                    getattr(record, state_field), getattr(record, state_field)
                ),
                "owners": [record.host.user.name or record.host.user.email]
                if key == "events"
                else [
                    p.user.name or p.user.email
                    for p in record.assigned_to.all()
                    if p.org_id == org.pk
                ],
                "amount": str(record.amount)
                if key == "deals" and record.amount is not None
                else None,
                "currency": (record.currency or org.default_currency)
                if key == "deals"
                else None,
            }
            for record in rows
        ]
        response = Response(result)
        response["Cache-Control"] = "private, no-store"
        return response
