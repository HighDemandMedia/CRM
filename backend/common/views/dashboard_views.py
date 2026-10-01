from datetime import timedelta

from django.db.models import DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cases.models import Case
from common import serializer, swagger_params
from common.models import Activity
from common.permissions import HasOrgContext, is_org_admin
from common.rbac import activity_scoped
from common.utils import STAGES
from opportunity.models import Opportunity, StageAgingConfig
from opportunity.workflow import DEFAULT_STAGE_EXPECTED_DAYS, ROTTEN_MULTIPLIER
from tasks.models import Task

# Sales stages a deal can still be worked (and therefore "age") in: mirrors
# the open-stage list ApiHomeView uses for its revenue metrics.
OPEN_STAGES = ["PROSPECTING", "QUALIFICATION", "PROPOSAL", "NEGOTIATION"]

# Case statuses that are still open. The rest (Closed, Rejected, Duplicate) are
# terminal; listing the open ones explicitly means a new terminal status is a
# deliberate edit here, not a silent inclusion in the "needs a reply" queue.
OPEN_CASE_STATUSES = ["New", "Assigned", "Pending"]

# How many rows the Today queue shows, and how many each of its four sources
# contributes before ranking. Neither is a count of anything: `summary.count`
# is derived from the sources themselves, so raising or lowering these changes
# what is displayed and never what the header claims.
TODAY_QUEUE_LIMIT = 8
TODAY_SOURCE_LIMIT = 25

_CURRENCY_SYMBOL = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "INR": "₹",
    "AUD": "A$",
    "CAD": "C$",
}


def _fmt_money(amount, currency):
    """One-line money for a human sentence, e.g. '$42,000'. Falls back to
    'CODE 42,000' for currencies without a symbol. Formatting lives here only
    because the Today queue ships each row as one prebuilt line; every other
    endpoint returns structured numbers and lets the client format them."""
    n = float(amount or 0)
    sym = _CURRENCY_SYMBOL.get((currency or "").upper())
    return f"{sym}{n:,.0f}" if sym else f"{(currency or '').upper()} {n:,.0f}".strip()


def _fmt_date(d):
    """'Jul 5'. Portable (avoids the platform-specific %-d)."""
    return f"{d:%b} {d.day}"


def _owned_or_assigned(queryset, profile):
    """Narrow a queryset to what a non-admin may see, without joining.

    Filtering straight onto the ``assigned_to`` M2M multiplies rows: a record
    the member created that also carries three assignees comes back three
    times, because the OR forces a LEFT JOIN and every joined row satisfies the
    ``created_by`` half. That inflates ``.count()`` and, worse, ``Sum()``, so a
    member's pipeline total could read three times its real value.

    Resolving the ids in a subquery keeps the outer query at one row per
    record, which is what the counts and the aggregates below assume.
    """
    return queryset.filter(
        pk__in=queryset.filter(
            Q(assigned_to=profile) | Q(created_by=profile.user)
        ).values("pk")
    )


class ApiTodayView(APIView):
    """The v2 home ("Today"): one prioritised, cross-model action queue.

    Combines active workflows into a single ranked list:

      * support cases still awaiting a first response (SLA-breached first),
      * open deals that have gone quiet (stage-aging yellow/red),
      * tasks overdue or due today.

    Security: every query is org-scoped. The org comes from the JWT via
    middleware, never the client, and a member sees only rows assigned to or
    created by them. Admins see the
    whole org. ``HasOrgContext`` guarantees ``request.profile``/``org`` are set,
    so this never dereferences a ``None`` profile.
    """

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=["home"],
        parameters=swagger_params.organization_params,
        responses={
            200: inline_serializer(
                name="ApiTodayResponse",
                fields={
                    "queue": serializers.ListField(child=serializers.DictField()),
                    "summary": inline_serializer(
                        name="ApiTodaySummary",
                        fields={
                            "count": serializers.IntegerField(),
                            "shown": serializers.IntegerField(),
                            "sources": serializers.ListField(
                                child=serializers.DictField()
                            ),
                            "quiet_deals": serializers.IntegerField(),
                            "quiet_value": serializers.FloatField(),
                            "cleared_yesterday": serializers.IntegerField(),
                        },
                    ),
                    "later": serializers.ListField(child=serializers.DictField()),
                },
            )
        },
    )
    def get(self, request, format=None):
        org = request.profile.org
        profile = request.profile
        now = timezone.now()
        # The org's calendar day, not UTC's. `now.date()` put the whole "Today"
        # queue a day behind for every hour that TIME_ZONE is ahead of UTC.
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        week_end = today + timedelta(days=7)
        is_admin = is_org_admin(profile) or request.user.is_superuser
        org_currency = org.default_currency or "USD"

        def mine(qs):
            """Restrict a queryset to rows a member may see. ``created_by`` is a
            User FK (compared to ``profile.user``); ``assigned_to`` is an M2M of
            Profile: the OR-over-a-join can duplicate rows, so distinct()."""
            return qs.filter(
                Q(assigned_to__id__in=[profile.id]) | Q(created_by=profile.user)
            ).distinct()

        # ── base, org-scoped querysets ──────────────────────────────────────
        opportunities = Opportunity.objects.filter(org=org, stage__in=OPEN_STAGES)
        cases = Case.objects.filter(org=org, status__in=OPEN_CASE_STATUSES)
        tasks = Task.objects.filter(
            org=org, status__in=["New", "In Progress"], due_date__lte=today
        )
        if not is_admin:
            opportunities = mine(opportunities)
            cases = mine(cases)
            tasks = mine(tasks)

        # ── deal aging as DB date cutoffs (no per-row Python) ───────────────
        # For each open stage: "quiet" (yellow+) once the deal has sat past its
        # yellow threshold; "rotten" (red) at 1.5x expected. Translating the
        # thresholds to stage_changed_at cutoffs keeps this a filter, not a scan.
        aging_configs = {
            c.stage: c
            for c in StageAgingConfig.objects.filter(org=org, stage__in=OPEN_STAGES)
        }
        quiet_q = None
        rotten_cutoffs = {}
        for stage in OPEN_STAGES:
            cfg = aging_configs.get(stage)
            expected = (
                cfg.expected_days if cfg else DEFAULT_STAGE_EXPECTED_DAYS.get(stage)
            )
            if not expected:
                continue
            warning = cfg.warning_days if cfg else None
            yellow_days = min(warning, expected) if warning else expected
            yellow_cutoff = now - timedelta(days=yellow_days)
            rotten_cutoffs[stage] = now - timedelta(days=expected * ROTTEN_MULTIPLIER)
            clause = Q(stage=stage, stage_changed_at__lte=yellow_cutoff)
            quiet_q = clause if quiet_q is None else (quiet_q | clause)

        quiet_opps = (
            opportunities.filter(quiet_q)
            if quiet_q is not None
            else opportunities.none()
        )
        quiet_deals = quiet_opps.count()
        quiet_value = quiet_opps.filter(
            Q(currency=org_currency) | Q(currency__isnull=True) | Q(currency="")
        ).aggregate(total=Coalesce(Sum("amount"), 0, output_field=DecimalField()))[
            "total"
        ]

        # ── build the queue (each source pre-ordered by urgency, capped) ────
        queue = []
        awaiting_cases = cases.filter(first_response_at__isnull=True)

        # 1. Cases awaiting a first response. SLA-breached outrank in-SLA ones;
        #    High/Urgent priority render with the alarm tone.
        for c in awaiting_cases.select_related("account").order_by("created_at")[
            :TODAY_SOURCE_LIMIT
        ]:
            deadline = c.created_at + timedelta(hours=c.sla_first_response_hours or 4)
            breached = deadline < now
            hot = c.priority in ("High", "Urgent")
            queue.append(
                {
                    "_rank": 0 if breached else 3,
                    "id": f"case-{c.id}",
                    "tone": "rust" if (hot or breached) else "clay",
                    "due": "Overdue" if breached else "Today",
                    "title": c.name,
                    "detail": f"{c.priority} · {c.account.name if c.account_id else 'No account'} · awaiting first reply",
                    "action": "Reply",
                    "href": f"/tickets/{c.id}",
                }
            )

        # 3. Quiet deals (aging). Rotten (red) outrank merely slowing (yellow).
        stage_labels = dict(STAGES)
        for opp in quiet_opps.order_by("stage_changed_at")[:TODAY_SOURCE_LIMIT]:
            rotten = (
                opp.stage in rotten_cutoffs
                and opp.stage_changed_at is not None
                and opp.stage_changed_at <= rotten_cutoffs[opp.stage]
            )
            days = (now - opp.stage_changed_at).days if opp.stage_changed_at else 0
            queue.append(
                {
                    "_rank": 2 if rotten else 6,
                    "id": f"deal-{opp.id}",
                    "tone": "rust" if rotten else "clay",
                    "due": "Stalled" if rotten else "Aging",
                    "title": opp.name,
                    "detail": f"No movement for {days} days · {_fmt_money(opp.amount, opp.currency)} · {stage_labels.get(opp.stage, opp.stage)}",
                    "action": "Open the deal",
                    "href": f"/pipeline/{opp.id}",
                }
            )

        # 4. Tasks overdue or due today.
        for t in tasks.order_by("due_date")[:TODAY_SOURCE_LIMIT]:
            overdue = t.due_date is not None and t.due_date < today
            queue.append(
                {
                    "_rank": 4 if overdue else 5,
                    "id": f"task-{t.id}",
                    "tone": "clay" if overdue else "slate",
                    "due": "Overdue" if overdue else "Today",
                    "title": t.title,
                    "detail": (
                        f"Due {_fmt_date(t.due_date)} · {t.priority}"
                        if t.due_date
                        else t.priority
                    ),
                    "action": "Open the task",
                    "href": f"/tasks/{t.id}",
                }
            )

        queue.sort(key=lambda item: item["_rank"])
        queue = [
            {k: v for k, v in item.items() if k != "_rank"}
            for item in queue[:TODAY_QUEUE_LIMIT]
        ]

        # ── the count, and where the rows that did not fit have gone ────────
        # `len(queue)` was a third number that matched nothing on screen: it is
        # taken after the per-source cap and before the queue cap, so the header
        # could claim 42 over 8 rows, and an org past the source cap would get
        # neither its true total nor its visible one. Count each source instead,
        # and hand the page a per-source breakdown so the overflow has somewhere
        # to go. The hrefs are literals built here, never stored values.
        sources = [
            {
                "label": "tickets awaiting a reply",
                "count": awaiting_cases.count(),
                "href": "/tickets",
            },
            {"label": "quiet deals", "count": quiet_deals, "href": "/pipeline"},
            {"label": "tasks due", "count": tasks.count(), "href": "/tasks"},
        ]
        sources = [s for s in sources if s["count"]]
        total_urgent = sum(s["count"] for s in sources)

        # ── "cleared yesterday" (a morale line) ─────────────────────────────
        # Tasks have no completed_at, so proxy with "marked Completed and last
        # touched yesterday"; cases carry a real closed_on date.
        cleared_tasks = Task.objects.filter(
            org=org, status="Completed", updated_at__date=yesterday
        )
        cleared_cases = Case.objects.filter(
            org=org, status="Closed", closed_on=yesterday
        )
        if not is_admin:
            cleared_tasks = mine(cleared_tasks)
            cleared_cases = mine(cleared_cases)

        summary = {
            "count": total_urgent,
            "shown": len(queue),
            "sources": sources,
            "quiet_deals": quiet_deals,
            "quiet_value": float(quiet_value or 0),
            "cleared_yesterday": cleared_tasks.count() + cleared_cases.count(),
        }

        # ── "later this week" (due tomorrow … +7 days) ──────────────────────
        soon = Q(due_date__gt=today, due_date__lte=week_end)
        later_tasks = Task.objects.filter(
            org=org, status__in=["New", "In Progress"]
        ).filter(soon)
        later_opps = Opportunity.objects.filter(
            org=org, stage__in=OPEN_STAGES, closed_on__gt=today, closed_on__lte=week_end
        )
        if not is_admin:
            later_tasks = mine(later_tasks)
            later_opps = mine(later_opps)

        later_rows = []
        for t in later_tasks.order_by("due_date")[:10]:
            later_rows.append(
                (
                    t.due_date,
                    {
                        "id": f"task-{t.id}",
                        "day": t.due_date.strftime("%a"),
                        "title": t.title,
                        "meta": f"Task · {t.priority}",
                    },
                )
            )
        for o in later_opps.order_by("closed_on")[:10]:
            later_rows.append(
                (
                    o.closed_on,
                    {
                        "id": f"deal-{o.id}",
                        "day": o.closed_on.strftime("%a"),
                        "title": f"{o.name} expected to close",
                        "meta": f"{stage_labels.get(o.stage, o.stage)} · {_fmt_money(o.amount, o.currency)}",
                    },
                )
            )
        later_rows.sort(key=lambda r: r[0])
        later = [row for _, row in later_rows[:6]]

        return Response(
            {"queue": queue, "summary": summary, "later": later},
            status=status.HTTP_200_OK,
        )


class ActivityListView(APIView):
    """
    Get recent activities for the organization
    Returns the last 10 activities by default
    """

    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(
        tags=["activities"],
        parameters=swagger_params.organization_params
        + [
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of activities to return (default: 10, max: 50)",
            ),
            OpenApiParameter(
                name="entity_type",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by entity type (Account, Lead, Contact, etc.)",
            ),
        ],
        responses={200: serializer.DashboardActivitySerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        if not request.profile:
            return Response(
                {"error": True, "errors": "Organization context required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get query params
        limit = min(int(request.query_params.get("limit", 10)), 50)
        entity_type = request.query_params.get("entity_type", None)

        # Query activities for this organization
        queryset = activity_scoped(Activity.objects.all(), request.profile)

        # Filter by entity type if specified
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)

        # Get most recent activities
        activities = queryset.select_related("user", "user__user")[:limit]

        # Serialize
        activities_data = serializer.DashboardActivitySerializer(
            activities, many=True
        ).data

        return Response(
            {
                "error": False,
                "count": len(activities_data),
                "activities": activities_data,
            },
            status=status.HTTP_200_OK,
        )
