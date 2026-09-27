from common.rbac import calendar_scoped, permitted
from datetime import datetime, time, timedelta
from django.db.models import Q, F, Value, ExpressionWrapper, DateField, DurationField, IntegerField
from django.db.models.functions import Cast
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from common.models import Profile, SalesAppointment
from common.permissions import HasOrgContext, is_org_admin
from tasks.models import Task
from cases.models import Case
from opportunity.models import Opportunity


class TodaySummaryView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        org = request.profile.org
        admin = is_org_admin(request.profile)
        chosen = request.query_params.get('user') or str(request.profile.pk)
        people = Profile.objects.filter(org=org, is_active=True, user__is_active=True).select_related('user')
        if not admin:
            people = people.filter(pk=request.profile.pk)
            if chosen != str(request.profile.pk):
                return Response({'detail': 'You can only view your own day.'}, status=403)
        selected = None
        if chosen != 'all':
            selected = get_object_or_404(people, pk=serializers.UUIDField().run_validation(chosen))
        elif not admin:
            return Response(status=403)
        today = timezone.localdate()
        start = timezone.make_aware(datetime.combine(today, time.min))
        end = timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min))
        tasks = Task.objects.filter(org=org, due_date__lte=today).exclude(status='Completed')
        reminders = Task.objects.filter(org=org, due_date__gt=today).exclude(status='Completed')
        reminder_limit = ExpressionWrapper(
            Value(today, output_field=DateField()) + ExpressionWrapper(Cast(F('reminder_days'), IntegerField()) * Value(timedelta(days=1)), output_field=DurationField()),
            output_field=DateField(),
        )
        reminders = reminders.filter(reminder_days__isnull=False, due_date__lte=reminder_limit)
        deals = Opportunity.objects.filter(org=org, is_active=True, closed_on__lte=today).exclude(stage__in=['CLOSED_WON', 'CLOSED_LOST'])
        tickets = Case.objects.filter(org=org, is_active=True, due_at__lt=end).exclude(status__in=['Resolved','Closed','Rejected','Duplicate'])
        events = SalesAppointment.objects.filter(org=org, cancelled_at__isnull=True, starts_at__lt=end, ends_at__gt=start)
        events = calendar_scoped(events,request.profile)
        if selected:
            def mine(rows):
                return rows.filter(Q(assigned_to=selected) | Q(assigned_to__isnull=True, created_by=selected.user)).distinct()
            tasks, deals, tickets = mine(tasks), mine(deals), mine(tickets)
            reminders = mine(reminders)
            events = events.filter(host=selected)
        counts = {'events': events.count(), 'tasks_today': tasks.filter(due_date=today).count(), 'tasks': tasks.count(), 'deals': deals.count(), 'tickets': tickets.count()}
        counts['reminders'] = reminders.count()
        counts['overdue'] = tasks.filter(due_date__lt=today).count() + deals.filter(closed_on__lt=today).count() + tickets.filter(due_at__lt=start).count()
        agenda = []
        for event in events.select_related('contact', 'company', 'host__user').order_by('starts_at','pk')[:20]:
            attendee = event.contact or event.company
            if attendee is not None and not permitted(request.profile,attendee): attendee = None
            attendee_type = 'contact' if event.contact_id else 'company'
            agenda.append({'id':f'appointment:{event.pk}', 'type':'appointment', 'title':event.title, 'start':event.starts_at.isoformat(), 'end':event.ends_at.isoformat(), 'host':event.host.user.name or event.host.user.email, 'hostId':str(event.host_id), 'notes':event.internal_notes, 'attendee':{'id':str(attendee.pk), 'name':attendee.name, 'type':attendee_type} if attendee else None, 'phone':attendee.phone if attendee else '', 'email':attendee.email if attendee else '', 'language':attendee.language if attendee else ''})
        return Response({
            'date':today.isoformat(), 'timezone':timezone.get_current_timezone_name(), 'selected_user':chosen,
            'current_user':str(request.profile.pk), 'can_select_user':admin, 'people':[{'id':str(person.pk), 'name':person.user.name or person.user.email} for person in people],
            'counts':counts, 'events':agenda,
            'reminders': [{'id': str(row.pk), 'name': row.title, 'due': row.due_date, 'priority': row.priority} for row in reminders.order_by('due_date', 'pk')[:10]],
            'tasks':[{'id':str(row.pk), 'name':row.title, 'status':row.status, 'priority':row.priority, 'due':row.due_date, 'overdue':row.due_date < today} for row in tasks.order_by('due_date','pk')[:5]],
            'deals':[{'id':str(row.pk), 'name':row.name, 'stage':row.get_stage_display(), 'amount':row.amount, 'currency':row.currency or org.default_currency, 'due':row.closed_on, 'overdue':row.closed_on < today} for row in deals.order_by('closed_on','pk')[:5]],
            'tickets':[{'id':str(row.pk), 'name':row.name, 'code':row.ticket_code, 'priority':row.priority, 'due':timezone.localtime(row.due_at).date(), 'overdue':row.due_at < start} for row in tickets.order_by('due_at','pk')[:5]],
        })
