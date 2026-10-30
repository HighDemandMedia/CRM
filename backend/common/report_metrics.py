"""Object-specific metrics over an already permission- and period-scoped queryset."""

from django.db.models import Avg, Count, F, Q, Sum

from cases.workflow import TERMINAL_STATUSES
from opportunity.workflow import CLOSED_STAGES


def metric(key, label, value, definition, unit="count"):
    return {
        "key": key,
        "label": label,
        "value": value,
        "unit": unit,
        "definition": definition,
    }


def percentage(part, total):
    return round(part * 100 / total, 1) if total else None


def object_metrics(qs, key, total, *, now, today):
    # Do not join owners into the aggregate: a multi-owner record counts once.
    unassigned = Q(assigned_to__isnull=True)
    if key in ("contacts", "companies"):
        values = qs.aggregate(
            qualified=Count("pk", filter=Q(stage="QUALIFIED")),
            follow_up=Count("pk", filter=Q(stage="FOLLOW_UP")),
        )
        return [
            metric(
                "qualified",
                "Qualified share",
                percentage(values["qualified"], total),
                "Currently qualified records / all records in this selection.",
                "percent",
            ),
            metric(
                "follow_up",
                "Awaiting follow-up",
                values["follow_up"],
                "Records currently in the Follow Up stage in this selection.",
            ),
            metric(
                "unassigned",
                "Without owner",
                qs.filter(unassigned).count(),
                "Records in this selection with no assigned owner.",
            ),
        ]
    if key == "deals":
        values = qs.aggregate(
            won=Count("pk", filter=Q(stage="CLOSED_WON")),
            lost=Count("pk", filter=Q(stage="CLOSED_LOST")),
            overdue=Count(
                "pk", filter=~Q(stage__in=CLOSED_STAGES) & Q(closed_on__lt=today)
            ),
        )
        return [
            metric(
                "win_rate",
                "Win rate",
                percentage(values["won"], values["won"] + values["lost"]),
                "Won / (won + lost) among the selected records, using their current stages.",
                "percent",
            ),
            metric(
                "overdue",
                "Past expected close",
                values["overdue"],
                "Open deals in this selection whose expected close date is before today.",
            ),
        ]
    if key == "tasks":
        values = qs.aggregate(
            completed=Count("pk", filter=Q(status="Completed")),
            overdue=Count("pk", filter=~Q(status="Completed") & Q(due_date__lt=today)),
        )
        return [
            metric(
                "completion",
                "Completion rate",
                percentage(values["completed"], total),
                "Currently completed tasks / all tasks in this selection.",
                "percent",
            ),
            metric(
                "overdue",
                "Overdue tasks",
                values["overdue"],
                "Incomplete tasks in this selection with a due date before today.",
            ),
            metric(
                "unassigned",
                "Without owner",
                qs.filter(unassigned).count(),
                "Records in this selection with no assigned owner.",
            ),
        ]
    if key == "tickets":
        active = ~Q(status__in=TERMINAL_STATUSES)
        valid_resolution = Q(
            status__in=("Resolved", "Closed"), resolved_at__gte=F("created_at")
        )
        values = qs.aggregate(
            active=Count("pk", filter=active),
            overdue=Count("pk", filter=active & Q(due_at__lt=now)),
            resolution=Avg(F("resolved_at") - F("created_at"), filter=valid_resolution),
        )
        duration = values["resolution"]
        return [
            metric(
                "active",
                "Open tickets",
                values["active"],
                "Selected tickets excluding Resolved, Closed, Rejected and Duplicate.",
            ),
            metric(
                "overdue",
                "Overdue tickets",
                values["overdue"],
                "Open tickets in this selection whose due time has passed.",
            ),
            metric(
                "resolution",
                "Average resolution",
                round(duration.total_seconds() / 3600, 1)
                if duration is not None
                else None,
                "Elapsed hours from creation to recorded resolution for resolved or closed tickets. Excludes missing or invalid timestamps.",
                "hours",
            ),
        ]
    if key == "events":
        active = Q(cancelled_at__isnull=True)
        values = qs.aggregate(
            upcoming=Count("pk", filter=active & Q(starts_at__gte=now)),
            cancelled=Count("pk", filter=Q(cancelled_at__isnull=False)),
            duration=Sum(F("ends_at") - F("starts_at"), filter=active),
        )
        return [
            metric(
                "upcoming",
                "Upcoming events",
                values["upcoming"],
                "Non-cancelled events in this selection that have not started yet.",
            ),
            metric(
                "cancelled",
                "Cancellation rate",
                percentage(values["cancelled"], total),
                "Cancelled events / all events in this selection.",
                "percent",
            ),
            metric(
                "hours",
                "Scheduled hours",
                round(values["duration"].total_seconds() / 3600, 1)
                if values["duration"]
                else 0,
                "Sum of non-cancelled event durations in this selection, not attendance or unique busy time.",
                "hours",
            ),
        ]
    return []
