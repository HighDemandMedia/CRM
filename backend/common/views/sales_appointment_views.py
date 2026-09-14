from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from accounts.models import Account
from contacts.models import Contact
from datetime import timedelta
from django.db.models import Q
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from common.models import SalesAppointment, Profile, Activity
from common.permissions import HasOrgContext, is_org_admin


def sync_attendee(appointment, request, action, previous_start=None):
    model = Contact if appointment.contact_id else Account if appointment.company_id else None
    if not model:
        return
    attendee_id = appointment.contact_id or appointment.company_id
    attendee = model.objects.select_for_update().get(pk=attendee_id, org=appointment.org)
    before = attendee.appointment_at
    after = before
    if action == 'scheduled' or before == previous_start:
        after = appointment.starts_at
        if action == 'cancelled':
            relation = {'contact_id':attendee_id} if model is Contact else {'company_id':attendee_id}
            after = SalesAppointment.objects.filter(org=appointment.org, cancelled_at__isnull=True, starts_at__gte=timezone.now(), **relation).exclude(pk=appointment.pk).order_by('starts_at').values_list('starts_at',flat=True).first()
        model.objects.filter(pk=attendee_id, org=appointment.org).update(appointment_at=after, updated_at=timezone.now())
    Activity.objects.create(
        org=appointment.org, user=request.profile,
        entity_type='Contact' if model is Contact else 'Account', entity_id=attendee.pk,
        entity_name=attendee.name[:255], action='UPDATE',
        description=f'Event {action}: {appointment.title}',
        metadata={'actor':request.user.email, 'resource':{'type':'SalesAppointment','id':str(appointment.pk)},
                  'changes':{'appointment_at':{'label':'Appointment','before':before.isoformat() if before else None,'after':after.isoformat() if after else None}},
                  'event_start':appointment.starts_at.isoformat(),'event_end':appointment.ends_at.isoformat()})


def attendees_for(model, request):
    records = model.objects.filter(org=request.profile.org, is_active=True)
    if not is_org_admin(request.profile):
        records = records.filter(Q(assigned_to=request.profile) | Q(created_by=request.user)).distinct()
    return records


class AppointmentAttendeesView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        search = request.query_params.get('search', '').strip()[:255]
        contacts = attendees_for(Contact, request)
        companies = attendees_for(Account, request)
        if search:
            contacts = contacts.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(email__icontains=search) | Q(phone__icontains=search))
            companies = companies.filter(Q(name__icontains=search) | Q(email__icontains=search))
        return Response({
            'contacts': [{'id':str(c.pk), 'name':c.name or c.email or 'Unnamed contact'} for c in contacts.order_by('first_name','id')[:30]],
            'companies': [{'id':str(c.pk), 'name':c.name} for c in companies.order_by('name','id')[:30]],
        })


class AppointmentSerializer(serializers.ModelSerializer):
    attendee = serializers.SerializerMethodField()

    def get_attendee(self, obj):
        record = obj.contact or obj.company
        if not record or record.org_id != obj.org_id:
            return None
        return {'id':str(record.pk), 'type':'contact' if obj.contact_id else 'company', 'name':record.name, 'language':record.language or '', 'phone':record.phone or '', 'email':record.email or ''}

    host_name = serializers.CharField(source='host.user.email', read_only=True)

    class Meta:
        model = SalesAppointment
        fields = ('id', 'title', 'host', 'host_name', 'starts_at', 'ends_at', 'internal_notes', 'contact', 'company', 'attendee')
        read_only_fields = ('id',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['contact'].queryset = attendees_for(Contact, self.context['request'])
        self.fields['company'].queryset = attendees_for(Account, self.context['request'])
        self.fields['host'].queryset = Profile.objects.filter(org=self.context['request'].profile.org, is_active=True, user__is_active=True)

    def validate(self, attrs):
        if attrs.get("contact") and attrs.get("company"):
            raise serializers.ValidationError("Select one contact or company.")
        if attrs['ends_at'] <= attrs['starts_at']:
            raise serializers.ValidationError({'ends_at': 'End time must be after start time.'})
        return attrs


def lock_host_and_check(request, host_id, start, end, exclude=None):
    # Serialize bookings even when there are no existing events to lock.
    get_object_or_404(Profile.objects.select_for_update(), pk=host_id, org=request.profile.org, is_active=True, user__is_active=True)
    conflicts = SalesAppointment.objects.filter(org=request.profile.org, host_id=host_id, cancelled_at__isnull=True, starts_at__lt=end, ends_at__gt=start)
    if exclude:
        conflicts = conflicts.exclude(pk=exclude)
    if conflicts.exists():
        raise serializers.ValidationError('This host is already booked during that time. Choose another time.')


class AppointmentAvailabilityView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        host_id = serializers.UUIDField().run_validation(request.query_params.get('host'))
        get_object_or_404(Profile, pk=host_id, org=request.profile.org, is_active=True, user__is_active=True)
        field = serializers.DateTimeField()
        start = field.run_validation(request.query_params.get('start'))
        end = field.run_validation(request.query_params.get('end'))
        if end <= start or end-start > timedelta(days=2):
            raise serializers.ValidationError('Invalid availability range.')
        records = SalesAppointment.objects.filter(org=request.profile.org,host_id=host_id,cancelled_at__isnull=True,starts_at__lt=end,ends_at__gt=start)
        exclude=request.query_params.get('exclude')
        if exclude:
            records=records.exclude(pk=serializers.UUIDField().run_validation(exclude))
        # Free/busy only: other users' titles, attendees and notes stay private.
        return Response({'busy':list(records.order_by('starts_at').values('starts_at','ends_at'))})


class SalesAppointmentView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        field = serializers.DateTimeField()
        start = field.run_validation(request.query_params.get('start'))
        end = field.run_validation(request.query_params.get('end'))
        if end <= start or end - start > timedelta(days=43):
            raise serializers.ValidationError('Invalid calendar range.')
        records = SalesAppointment.objects.filter(org=request.profile.org, cancelled_at__isnull=True, starts_at__lt=end, ends_at__gt=start).select_related('host__user', 'contact', 'company').order_by('starts_at', 'id')
        if not is_org_admin(request.profile):
            records = records.filter(Q(host=request.profile) | Q(created_by=request.user))
        return Response(AppointmentSerializer(records, many=True, context={'request': request}).data)

    @transaction.atomic
    def post(self, request):
        serializer = AppointmentSerializer(data=request.data, context={'request':request})
        serializer.is_valid(raise_exception=True)
        values=serializer.validated_data
        lock_host_and_check(request, values['host'].pk, values['starts_at'], values['ends_at'])
        appointment = serializer.save(org=request.profile.org, created_by=request.user)
        sync_attendee(appointment, request, "scheduled")
        return Response(serializer.data, status=201)


class SalesAppointmentManageView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    @transaction.atomic
    def patch(self, request, pk):
        records = SalesAppointment.objects.filter(org=request.profile.org)
        if not is_org_admin(request.profile):
            records = records.filter(Q(host=request.profile) | Q(created_by=request.user))
        record = get_object_or_404(records, pk=pk)
        get_object_or_404(Profile.objects.select_for_update(), pk=record.host_id, org=request.profile.org)
        record = get_object_or_404(records.select_for_update(), pk=pk)
        operation = request.data.get('operation')
        if operation not in ('cancel', 'reschedule'):
            raise serializers.ValidationError('Invalid event action.')
        if record.cancelled_at:
            if operation == 'cancel':
                return Response({'cancelled': True})
            return Response({'message':'This event has already been cancelled.'}, status=409)
        previous_start = record.starts_at
        now = timezone.now()
        entry = {'action':operation, 'at':now.isoformat(), 'by':str(request.user.pk), 'email':request.user.email, 'previous_start':record.starts_at.isoformat(), 'previous_end':record.ends_at.isoformat()}
        if operation == 'cancel':
            record.cancelled_at = now
            record.cancelled_by = request.user
        else:
            field = serializers.DateTimeField()
            start = field.run_validation(request.data.get('starts_at'))
            end = field.run_validation(request.data.get('ends_at'))
            if end <= start:
                raise serializers.ValidationError('End time must be after start time.')
            lock_host_and_check(request, record.host_id, start, end, exclude=record.pk)
            record.starts_at, record.ends_at = start, end
            entry.update(start=start.isoformat(), end=end.isoformat())
        record.change_history = [*record.change_history, entry]
        record.save(update_fields=['starts_at','ends_at','cancelled_at','cancelled_by','change_history'])
        sync_attendee(record, request, 'cancelled' if operation == 'cancel' else 'rescheduled', previous_start)
        return Response({'saved':True})
