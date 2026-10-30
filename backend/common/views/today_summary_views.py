from datetime import datetime, time, timedelta

from django.db.models import (
    Case as DbCase,
)
from django.db.models import (
    DateField,
    DurationField,
    ExpressionWrapper,
    F,
    IntegerField,
    Q,
    Value,
    When,
)
from django.db.models.functions import Cast, TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cases.models import Case
from common.models import Profile, SalesAppointment
from common.permissions import HasOrgContext, is_org_admin
from common.platform_access import is_platform_owner
from common.rbac import calendar_scoped, permitted, scoped
from opportunity.models import Opportunity
from tasks.models import Task

PREVIEW_LIMIT = 7


def priority_order():
    return DbCase(
        When(priority="Urgent", then=Value(0)),
        When(priority="High", then=Value(1)),
        When(priority="Low", then=Value(3)),
        default=Value(2),
        output_field=IntegerField(),
    )


def task_preview(rows, profile, today):
    rows = list(
        rows.annotate(priority_rank=priority_order()).order_by(
            "due_date", "priority_rank", "pk"
        )[:PREVIEW_LIMIT]
    )
    # One scope check for the preview, rather than one query per completion button.
    completable = set(
        scoped(
            Task.objects.filter(pk__in=[row.pk for row in rows]), profile, "stage"
        ).values_list("pk", flat=True)
    )
    return [
        {
            "id": str(row.pk),
            "name": row.title,
            "status": row.status,
            "priority": row.priority,
            "due": row.due_date,
            "overdue": row.due_date < today,
            "can_complete": row.pk in completable,
        }
        for row in rows
    ]


def deal_preview(rows, currency, today):
    return [
        {
            "id": str(row.pk),
            "name": row.name,
            "stage": row.get_stage_display(),
            "amount": row.amount,
            "currency": row.currency or currency,
            "due": row.closed_on,
            "overdue": row.closed_on < today,
        }
        for row in rows.order_by("closed_on", "pk")[:PREVIEW_LIMIT]
    ]


class TodaySummaryView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        org = request.profile.org
        admin = is_org_admin(request.profile)
        # Support profiles have no personal workload in the customer's account.
        # Open its organization-wide day while retaining the real actor identity.
        platform_visit = request.profile.is_platform_access and is_platform_owner(
            request.user
        )
        chosen = request.query_params.get("user") or (
            "all" if platform_visit and admin else str(request.profile.pk)
        )
        people = Profile.objects.filter(
            org=org, is_active=True, user__is_active=True
        ).select_related("user")
        if not admin:
            people = people.filter(pk=request.profile.pk)
            if chosen != str(request.profile.pk):
                return Response(
                    {"detail": "You can only view your own day."}, status=403
                )
        selected = None
        if chosen != "all":
            selected = get_object_or_404(
                people, pk=serializers.UUIDField().run_validation(chosen)
            )
        elif not admin:
            return Response(status=403)
        now = timezone.now()
        today = timezone.localdate(now)
        week_end = today + timedelta(days=6 - today.weekday())
        start = timezone.make_aware(datetime.combine(today, time.min))
        end = timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min))
        tasks = Task.objects.filter(org=org, due_date__lte=today).exclude(
            status="Completed"
        )
        reminders = Task.objects.filter(org=org, due_date__gt=today).exclude(
            status="Completed"
        )
        reminder_limit = ExpressionWrapper(
            Value(today, output_field=DateField())
            + ExpressionWrapper(
                Cast(F("reminder_days"), IntegerField()) * Value(timedelta(days=1)),
                output_field=DurationField(),
            ),
            output_field=DateField(),
        )
        reminders = reminders.filter(
            reminder_days__isnull=False, due_date__lte=reminder_limit
        )
        deals = Opportunity.objects.filter(
            org=org, is_active=True, closed_on__lte=today
        ).exclude(stage__in=["CLOSED_WON", "CLOSED_LOST"])
        weekly_deals = Opportunity.objects.filter(
            org=org, is_active=True, closed_on__range=(today, week_end)
        ).exclude(stage__in=["CLOSED_WON", "CLOSED_LOST"])
        tickets = Case.objects.filter(org=org, is_active=True, due_at__lt=end).exclude(
            status__in=["Resolved", "Closed", "Rejected", "Duplicate"]
        )
        events = SalesAppointment.objects.filter(
            org=org, cancelled_at__isnull=True, starts_at__lt=end, ends_at__gt=start
        )
        events = calendar_scoped(events, request.profile)
        if selected:

            def mine(rows):
                return rows.filter(
                    Q(assigned_to=selected)
                    | Q(assigned_to__isnull=True, created_by=selected.user)
                ).distinct()

            tasks, deals, tickets = mine(tasks), mine(deals), mine(tickets)
            reminders = mine(reminders)
            weekly_deals = mine(weekly_deals)
            events = events.filter(host=selected)
        counts = {
            "events": events.count(),
            "tasks_today": tasks.filter(due_date=today).count(),
            "tasks": tasks.count(),
            "deals": deals.count(),
            "tickets": tickets.count(),
            "weekly_deals": weekly_deals.count(),
        }
        counts["reminders"] = reminders.count()
        counts["overdue"] = (
            tasks.filter(due_date__lt=today).count()
            + deals.filter(closed_on__lt=today).count()
            + tickets.filter(due_at__lt=start).count()
        )
        agenda = []
        for event in (
            events.select_related("contact", "company", "host__user")
            .annotate(
                finished=DbCase(When(ends_at__lte=now, then=Value(1)), default=Value(0))
            )
            .order_by("finished", "starts_at", "pk")[:20]
        ):
            attendee = event.contact or event.company
            if attendee is not None and not permitted(request.profile, attendee):
                attendee = None
            attendee_type = "contact" if event.contact_id else "company"
            agenda.append(
                {
                    "id": f"appointment:{event.pk}",
                    "type": "appointment",
                    "title": event.title,
                    "start": event.starts_at.isoformat(),
                    "end": event.ends_at.isoformat(),
                    "host": event.host.user.name or event.host.user.email,
                    "hostId": str(event.host_id),
                    "notes": event.internal_notes,
                    "attendee": {
                        "id": str(attendee.pk),
                        "name": attendee.name,
                        "type": attendee_type,
                    }
                    if attendee
                    else None,
                    "phone": attendee.phone if attendee else "",
                    "email": attendee.email if attendee else "",
                    "language": attendee.language if attendee else "",
                }
            )
        return Response(
            {
                "date": today.isoformat(),
                "now": now.isoformat(),
                "week_end": week_end.isoformat(),
                "timezone": timezone.get_current_timezone_name(),
                "selected_user": chosen,
                "current_user": str(request.profile.pk),
                "can_select_user": admin,
                "people": [
                    {
                        "id": str(person.pk),
                        "name": person.user.name or person.user.email,
                    }
                    for person in people
                ],
                "counts": counts,
                "events": agenda,
                "reminders": task_preview(reminders, request.profile, today),
                "tasks": task_preview(tasks, request.profile, today),
                # A separate bounded preview keeps today's tasks available even
                # when a large overdue backlog fills the default preview.
                "tasks_today": task_preview(
                    tasks.filter(due_date=today), request.profile, today
                ),
                "deals": deal_preview(deals, org.default_currency, today),
                "weekly_deals": deal_preview(weekly_deals, org.default_currency, today),
                "tickets": [
                    {
                        "id": str(row.pk),
                        "name": row.name,
                        "code": row.ticket_code,
                        "priority": row.priority,
                        "due": timezone.localtime(row.due_at).date(),
                        "overdue": row.due_at < start,
                    }
                    for row in tickets.annotate(
                        due_day=TruncDate(
                            "due_at", tzinfo=timezone.get_current_timezone()
                        ),
                        priority_rank=priority_order(),
                    ).order_by("due_day", "priority_rank", "pk")[:PREVIEW_LIMIT]
                ],
            }
        )
