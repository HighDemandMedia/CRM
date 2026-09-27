from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account
from common.models import Activity, Comment, Profile, SalesAppointment
from common.permissions import HasOrgContext, is_org_admin
from common.pipeline_settings import validate_entry
from common.rbac import (
    calendar_hosts,
    calendar_scoped,
    configured,
    permitted,
    require,
    require_record,
    validate_assignment,
)
from contacts.choices import CONTACT_SOURCES
from contacts.models import Contact
from opportunity.models import Opportunity


def external_attendees(appointment):
    records = [*appointment.contacts.all(), *appointment.companies.all()]
    if appointment.contact_id:
        records.append(appointment.contact)
    if appointment.company_id:
        records.append(appointment.company)
    return list(
        {
            (record._meta.label, record.pk): record
            for record in records
            if record.org_id == appointment.org_id
        }.values()
    )


def sync_attendee(appointment, request, action, previous_start=None):
    for record in sorted(
        external_attendees(appointment), key=lambda row: (row._meta.label, str(row.pk))
    ):
        model = type(record)
        attendee_id = record.pk
        attendee = model.objects.select_for_update().get(
            pk=attendee_id, org=appointment.org
        )
        if action == "scheduled" and appointment.internal_notes.strip():
            Comment.objects.create(
                content_type=ContentType.objects.get_for_model(model),
                object_id=attendee.pk,
                org=appointment.org,
                comment=appointment.internal_notes.strip(),
                commented_by=request.profile,
                is_internal=True,
            )
        before = attendee.appointment_at
        after = before
        if action == "scheduled" or before == previous_start:
            after = appointment.starts_at
            if action == "cancelled":
                relation = (
                    (Q(contact_id=attendee_id) | Q(contacts__id=attendee_id))
                    if model is Contact
                    else (Q(company_id=attendee_id) | Q(companies__id=attendee_id))
                )
                after = (
                    SalesAppointment.objects.filter(
                        relation,
                        org=appointment.org,
                        cancelled_at__isnull=True,
                        starts_at__gte=timezone.now(),
                    )
                    .distinct()
                    .exclude(pk=appointment.pk)
                    .order_by("starts_at")
                    .values_list("starts_at", flat=True)
                    .first()
                )
            model.objects.filter(pk=attendee_id, org=appointment.org).update(
                appointment_at=after, updated_at=timezone.now()
            )
        Activity.objects.create(
            org=appointment.org,
            user=request.profile,
            entity_type="Contact" if model is Contact else "Account",
            entity_id=attendee.pk,
            entity_name=attendee.name[:255],
            action="UPDATE",
            description=f"Event {action}: {appointment.title}",
            metadata={
                "actor": request.user.email,
                "resource": {"type": "SalesAppointment", "id": str(appointment.pk)},
                "changes": {
                    "appointment_at": {
                        "label": "Appointment",
                        "before": before.isoformat() if before else None,
                        "after": after.isoformat() if after else None,
                    }
                },
                "event_start": appointment.starts_at.isoformat(),
                "event_end": appointment.ends_at.isoformat(),
            },
        )


def attendees_for(model, request):
    records = model.objects.filter(org=request.profile.org, is_active=True)
    if not configured(request.profile) and not is_org_admin(request.profile):
        records = records.filter(
            Q(assigned_to=request.profile) | Q(created_by=request.user)
        ).distinct()
    return records


class AppointmentAttendeesView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        search = request.query_params.get("search", "").strip()[:255]
        contacts = attendees_for(Contact, request)
        companies = attendees_for(Account, request)
        users = Profile.objects.filter(
            org=request.profile.org, is_active=True, user__is_active=True
        ).select_related("user")
        if search:
            contacts = contacts.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
            )
            companies = companies.filter(
                Q(name__icontains=search) | Q(email__icontains=search)
            )
            users = users.filter(
                Q(user__name__icontains=search) | Q(user__email__icontains=search)
            )
        return Response(
            {
                "users": [
                    {
                        "id": str(profile.pk),
                        "name": profile.user.name or profile.user.email,
                        "email": profile.user.email,
                    }
                    for profile in users.order_by("user__email", "pk")[:30]
                ],
                "contacts": [
                    {"id": str(c.pk), "name": c.name or c.email or "Unnamed contact"}
                    for c in contacts.order_by("first_name", "id")[:30]
                ],
                "companies": [
                    {"id": str(c.pk), "name": c.name}
                    for c in companies.order_by("name", "id")[:30]
                ],
            }
        )


class AppointmentSerializer(serializers.ModelSerializer):
    attendee = serializers.SerializerMethodField()
    attendees = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()

    def get_can_manage(self, obj):
        return self.get_can_reschedule(obj) or self.get_can_cancel(obj)

    can_reschedule = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()

    def get_can_reschedule(self, obj):
        return calendar_scoped(
            SalesAppointment.objects.filter(pk=obj.pk),
            self.context["request"].profile,
            "edit",
        ).exists()

    def get_can_cancel(self, obj):
        return calendar_scoped(
            SalesAppointment.objects.filter(pk=obj.pk),
            self.context["request"].profile,
            "cancel",
        ).exists()

    users = serializers.PrimaryKeyRelatedField(
        source="attendee_users",
        many=True,
        required=False,
        queryset=Profile.objects.none(),
    )

    def get_attendees(self, obj):
        result = [
            {
                "id": str(record.pk),
                "type": "contact" if isinstance(record, Contact) else "company",
                "name": record.name,
                "language": record.language or "",
                "phone": record.phone or "",
                "email": record.email or "",
            }
            for record in external_attendees(obj)
            if permitted(self.context["request"].profile, record)
        ]
        result.extend(
            {
                "id": str(profile.pk),
                "type": "user",
                "name": profile.user.name or profile.user.email,
                "email": profile.user.email,
            }
            for profile in obj.attendee_users.all()
            if profile.org_id == obj.org_id
        )
        return result

    def get_attendee(self, obj):
        record = obj.contact or obj.company
        if (
            not record
            or record.org_id != obj.org_id
            or not permitted(self.context["request"].profile, record)
        ):
            return None
        return {
            "id": str(record.pk),
            "type": "contact" if obj.contact_id else "company",
            "name": record.name,
            "language": record.language or "",
            "phone": record.phone or "",
            "email": record.email or "",
        }

    host_name = serializers.CharField(source="host.user.name", read_only=True)

    class Meta:
        model = SalesAppointment
        fields = (
            "id",
            "title",
            "host",
            "host_name",
            "starts_at",
            "ends_at",
            "internal_notes",
            "contact",
            "company",
            "attendee",
            "attendees",
            "can_manage",
            "can_reschedule",
            "can_cancel",
            "contacts",
            "companies",
            "users",
            "deal",
        )
        read_only_fields = ("id", "deal")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["contact"].queryset = attendees_for(
            Contact, self.context["request"]
        )
        self.fields["company"].queryset = attendees_for(
            Account, self.context["request"]
        )
        self.fields["contacts"].child_relation.queryset = attendees_for(
            Contact, self.context["request"]
        )
        self.fields["companies"].child_relation.queryset = attendees_for(
            Account, self.context["request"]
        )
        self.fields["users"].child_relation.queryset = Profile.objects.filter(
            org=self.context["request"].profile.org,
            is_active=True,
            user__is_active=True,
        )
        self.fields["host"].queryset = calendar_hosts(self.context["request"].profile)

    def validate(self, attrs):
        if attrs.get("contact") and attrs.get("company"):
            raise serializers.ValidationError("Select one contact or company.")
        for key, legacy in [("contacts", "contact"), ("companies", "company")]:
            values = list(attrs.get(key, []))
            if attrs.get(legacy):
                values.append(attrs[legacy])
            attrs[key] = list({record.pk: record for record in values}.values())
        attrs["attendee_users"] = list(
            {record.pk: record for record in attrs.get("attendee_users", [])}.values()
        )
        for record in [*attrs["contacts"], *attrs["companies"]]:
            require_record(self.context["request"].profile, record, "edit")
            if attrs.get("internal_notes", "").strip():
                require_record(self.context["request"].profile, record, "notes")
        if (
            sum(len(attrs[key]) for key in ["contacts", "companies", "attendee_users"])
            > 100
        ):
            raise serializers.ValidationError("Select at most 100 attendees.")
        # Keep the primary legacy attendee for older clients and deal defaults.
        if not attrs.get("contact") and not attrs.get("company"):
            if attrs["contacts"]:
                attrs["contact"] = attrs["contacts"][0]
            elif attrs["companies"]:
                attrs["company"] = attrs["companies"][0]
        if attrs["ends_at"] <= attrs["starts_at"]:
            raise serializers.ValidationError(
                {"ends_at": "End time must be after start time."}
            )
        return attrs


def lock_host_and_check(
    request, host_id, start, end, exclude=None, allow_overlap=False
):
    # Serialize bookings even when there are no existing events to lock.
    get_object_or_404(
        Profile.objects.select_for_update(),
        pk=host_id,
        org=request.profile.org,
        is_active=True,
        user__is_active=True,
    )
    conflicts = SalesAppointment.objects.filter(
        Q(host_id=host_id) | Q(attendee_users__id=host_id),
        org=request.profile.org,
        cancelled_at__isnull=True,
        starts_at__lt=end,
        ends_at__gt=start,
    )
    if exclude:
        conflicts = conflicts.exclude(pk=exclude)
    if conflicts.exists() and allow_overlap:
        require(request.profile, "calendar", "override_conflicts")
    if conflicts.exists() and not allow_overlap:
        raise serializers.ValidationError(
            "This host is already booked during that time. Choose another time."
        )


class AppointmentAvailabilityView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        host_id = serializers.UUIDField().run_validation(
            request.query_params.get("host")
        )
        get_object_or_404(calendar_hosts(request.profile), pk=host_id)
        field = serializers.DateTimeField()
        start = field.run_validation(request.query_params.get("start"))
        end = field.run_validation(request.query_params.get("end"))
        if end <= start or end - start > timedelta(days=8):
            raise serializers.ValidationError("Invalid availability range.")
        records = SalesAppointment.objects.filter(
            Q(host_id=host_id) | Q(attendee_users__id=host_id),
            org=request.profile.org,
            cancelled_at__isnull=True,
            starts_at__lt=end,
            ends_at__gt=start,
        )
        exclude = request.query_params.get("exclude")
        if exclude:
            records = records.exclude(
                pk=serializers.UUIDField().run_validation(exclude)
            )
        visible_ids = set(
            calendar_scoped(records, request.profile).values_list("pk", flat=True)
        )
        return Response(
            {
                "busy": [
                    {
                        "starts_at": record.starts_at,
                        "ends_at": record.ends_at,
                        "title": record.title if record.pk in visible_ids else None,
                    }
                    for record in records.distinct()
                    .order_by("starts_at")
                    .only("starts_at", "ends_at", "title", "host_id", "created_by_id")
                ]
            }
        )


class SalesAppointmentView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        field = serializers.DateTimeField()
        start = field.run_validation(request.query_params.get("start"))
        end = field.run_validation(request.query_params.get("end"))
        if end <= start or end - start > timedelta(days=43):
            raise serializers.ValidationError("Invalid calendar range.")
        records = (
            SalesAppointment.objects.filter(
                org=request.profile.org,
                cancelled_at__isnull=True,
                starts_at__lt=end,
                ends_at__gt=start,
            )
            .select_related("host__user", "contact", "company")
            .prefetch_related("contacts", "companies", "attendee_users__user")
            .order_by("starts_at", "id")
        )
        records = calendar_scoped(records, request.profile)
        return Response(
            AppointmentSerializer(records, many=True, context={"request": request}).data
        )

    @transaction.atomic
    def post(self, request):
        require(request.profile, "calendar", "create")
        serializer = AppointmentSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        allow_overlap = serializers.BooleanField().run_validation(
            request.data.get("allow_overlap", False)
        )
        lock_host_and_check(
            request,
            values["host"].pk,
            values["starts_at"],
            values["ends_at"],
            allow_overlap=allow_overlap,
        )
        deal = None
        if serializers.BooleanField().run_validation(
            request.data.get("create_deal", False)
        ):
            require(request.profile, "deals", "create")
            require(request.profile, "deals", "associations")
            from types import SimpleNamespace

            validate_assignment(
                SimpleNamespace(
                    profile=request.profile,
                    data={"assigned_to": [str(values["host"].pk)]},
                ),
                "deals",
                None,
                creating=True,
            )
            attendee = values.get("contact") or values.get("company")
            if not attendee:
                raise serializers.ValidationError(
                    "Select an attendee to create a deal, or uncheck Create a deal."
                )
            source = request.data.get("deal_source") or attendee.source
            if source not in dict(CONTACT_SOURCES):
                raise serializers.ValidationError(
                    "Select a Source for the deal; the attendee has no source."
                )
            name = request.data.get("deal_name") or f"{attendee.name} - Deal"
            name = serializers.CharField(max_length=255).run_validation(name)
            copied = {
                key: getattr(attendee, key, None)
                for key in [
                    "phone",
                    "email",
                    "address_line",
                    "city",
                    "state",
                    "postcode",
                    "country",
                ]
            }
            deal_values = dict(
                name=name,
                org=request.profile.org,
                created_by=request.user,
                stage="PROSPECTING",
                priority="MEDIUM",
                lead_source=source,
                language=attendee.language or "",
                currency=request.profile.org.default_currency,
                account=values.get("company")
                or next(iter(values.get("companies", [])), None),
                **copied,
            )
            validate_entry(
                request.profile.org,
                "Opportunity",
                None,
                {
                    **deal_values,
                    "assigned_to": [values["host"]],
                    "contacts": values.get("contacts", []),
                },
            )
            deal = Opportunity.objects.create(**deal_values)
            deal.assigned_to.add(values["host"])
            deal.contacts.add(*values.get("contacts", []))
        appointment = serializer.save(
            org=request.profile.org, created_by=request.user, deal=deal
        )
        sync_attendee(appointment, request, "scheduled")
        return Response(serializer.data, status=201)


class SalesAppointmentManageView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    @transaction.atomic
    def patch(self, request, pk):
        operation = request.data.get("operation")
        action = "cancel" if operation == "cancel" else "edit"
        require(request.profile, "calendar", action)
        records = calendar_scoped(
            SalesAppointment.objects.all(), request.profile, action
        )
        record = get_object_or_404(records, pk=pk)
        for attendee in external_attendees(record):
            require_record(request.profile, attendee, "edit")
        get_object_or_404(
            Profile.objects.select_for_update(),
            pk=record.host_id,
            org=request.profile.org,
        )
        record = get_object_or_404(records.select_for_update(), pk=pk)
        operation = request.data.get("operation")
        if operation not in ("cancel", "reschedule"):
            raise serializers.ValidationError("Invalid event action.")
        if record.cancelled_at:
            if operation == "cancel":
                return Response({"cancelled": True})
            return Response(
                {"message": "This event has already been cancelled."}, status=409
            )
        previous_start = record.starts_at
        now = timezone.now()
        entry = {
            "action": operation,
            "at": now.isoformat(),
            "by": str(request.user.pk),
            "email": request.user.email,
            "previous_start": record.starts_at.isoformat(),
            "previous_end": record.ends_at.isoformat(),
        }
        if operation == "cancel":
            record.cancelled_at = now
            record.cancelled_by = request.user
        else:
            field = serializers.DateTimeField()
            start = field.run_validation(request.data.get("starts_at"))
            end = field.run_validation(request.data.get("ends_at"))
            if end <= start:
                raise serializers.ValidationError("End time must be after start time.")
            lock_host_and_check(request, record.host_id, start, end, exclude=record.pk)
            record.starts_at, record.ends_at = start, end
            entry.update(start=start.isoformat(), end=end.isoformat())
        record.change_history = [*record.change_history, entry]
        record.save(
            update_fields=[
                "starts_at",
                "ends_at",
                "cancelled_at",
                "cancelled_by",
                "change_history",
            ]
        )
        sync_attendee(
            record,
            request,
            "cancelled" if operation == "cancel" else "rescheduled",
            previous_start,
        )
        return Response({"saved": True})
