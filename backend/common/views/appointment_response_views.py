"""Anonymous RSVP: a signed, recipient-scoped capability; GET never mutates."""

import hashlib

from django.core import signing
from django.db import transaction
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from common.appointment_invitations import can_respond, read_token, response_for
from common.models import SalesAppointment
from common.request_meta import client_ip
from common.rls.context import org_context


class AppointmentResponseThrottle(SimpleRateThrottle):
    scope = "appointment_response"
    rate = "60/min"

    def get_cache_key(self, request, view):
        ident = client_ip(request) or "unknown"
        if request.method == "GET":
            # Server-rendered reads share Web's IP. Separate valid invitations,
            # while malformed tokens still share the ordinary abuse limit.
            try:
                values = read_token(request.query_params.get("token"))
                ident += (
                    ":" + hashlib.sha256("\n".join(values[:3]).encode()).hexdigest()
                )
            except (signing.BadSignature, ValueError, TypeError):
                pass
        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }


class AppointmentResponseView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (AppointmentResponseThrottle,)

    def get(self, request):
        return self.respond(request.query_params.get("token"))

    def post(self, request):
        status = request.data.get("response")
        if status not in {"accepted", "tentative", "declined"}:
            return Response({"message": "Choose a response."}, status=400)
        return self.respond(request.data.get("token"), status)

    def respond(self, token, status=None):
        try:
            org_id, appointment_id, email, start, end = read_token(token)
        except (signing.BadSignature, ValueError, TypeError):
            return Response(
                {"message": "This invitation is no longer available."}, status=410
            )
        with org_context(org_id), transaction.atomic():
            appointment = (
                SalesAppointment.objects.select_for_update()
                .select_related("org", "host__user")
                .filter(pk=appointment_id, org_id=org_id)
                .first()
            )
            if not appointment or not can_respond(appointment, email, start, end):
                return Response(
                    {
                        "message": "This invitation is no longer available. Use the latest invitation."
                    },
                    status=410,
                )
            if status:
                responses = {**appointment.guest_responses, email: status}
                SalesAppointment.objects.filter(
                    pk=appointment.pk, org_id=org_id
                ).update(guest_responses=responses)
                appointment.guest_responses = responses
            return Response(
                {
                    "title": appointment.title,
                    "organization": appointment.org.name,
                    "start": appointment.starts_at,
                    "end": appointment.ends_at,
                    "response": response_for(appointment, email),
                },
                headers={"Cache-Control": "private, no-store"},
            )
