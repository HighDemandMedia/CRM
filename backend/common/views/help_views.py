"""CRM product support email, independent of organization customer tickets."""

import hashlib
import json
import logging
import uuid

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMessage
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from common.permissions import HasOrgContext

SUPPORT_EMAIL = "info@highdemandmedia.com"
CATEGORIES = {"bug": "Bug report", "feature": "Feature request", "help": "Help request"}
REQUEST_FIELDS = {
    "bug": [
        ("actual", "What happened", True),
        ("expected", "Expected result", True),
        ("impact", "Effect on work", True),
        ("frequency", "Frequency", False),
        ("steps", "Steps to reproduce", False),
        ("record_link", "Affected page", False),
    ],
    "feature": [
        ("problem", "Problem or need", True),
        ("benefit", "Desired outcome", True),
        ("audience", "Who benefits", False),
        ("suggestion", "Proposed solution", False),
    ],
    "help": [
        ("question", "Question / task to accomplish", True),
        ("tried", "Already tried", False),
    ],
}
CHOICE_LABELS = {
    "impact": {
        "blocked": "Work is blocked",
        "workaround": "Can continue with a workaround",
        "minor": "Minor issue; can continue working",
    },
    "frequency": {
        "once": "Happened once",
        "sometimes": "Sometimes",
        "always": "Every time",
        "unknown": "Not sure yet",
    },
    "audience": {
        "me": "Requester",
        "team": "Their team",
        "organization": "Whole organization",
        "customers": "Their customers",
    },
}
AREAS = (
    "General",
    "Contacts",
    "Companies",
    "Deals",
    "Tasks",
    "Tickets",
    "Calendar",
    "Reports",
    "Profile",
    "Organization & access",
    "Properties, pipelines & tags",
)
logger = logging.getLogger(__name__)


def delivery_mode():
    backend = settings.EMAIL_BACKEND
    sandbox = (
        backend.endswith(
            (
                "console.EmailBackend",
                "locmem.EmailBackend",
                "filebased.EmailBackend",
                "dummy.EmailBackend",
            )
        )
        or getattr(settings, "EMAIL_HOST", "") == "mailpit"
    )
    if sandbox:
        return (
            "local_test"
            if settings.DEBUG and not backend.endswith("dummy.EmailBackend")
            else "unavailable"
        )
    return "email"


class SupportThrottle(SimpleRateThrottle):
    scope = "crm_support"
    rate = "10/hour"

    def get_cache_key(self, request, view):
        if request.method != "POST":
            return None
        return f"crm-support-rate:{request.user.pk}"


class SupportRequestSerializer(serializers.Serializer):
    request_id = serializers.UUIDField()
    category = serializers.ChoiceField(choices=list(CATEGORIES))
    area = serializers.ChoiceField(choices=AREAS)
    subject = serializers.CharField(max_length=160, required=False, allow_blank=True)
    steps = serializers.CharField(max_length=6000, required=False, allow_blank=True)
    actual = serializers.CharField(max_length=6000, required=False, allow_blank=True)
    expected = serializers.CharField(max_length=6000, required=False, allow_blank=True)
    problem = serializers.CharField(max_length=6000, required=False, allow_blank=True)
    suggestion = serializers.CharField(
        max_length=6000, required=False, allow_blank=True
    )
    benefit = serializers.CharField(max_length=6000, required=False, allow_blank=True)
    question = serializers.CharField(max_length=6000, required=False, allow_blank=True)
    tried = serializers.CharField(max_length=6000, required=False, allow_blank=True)

    impact = serializers.ChoiceField(
        choices=list(CHOICE_LABELS["impact"]), required=False, allow_blank=True
    )
    frequency = serializers.ChoiceField(
        choices=list(CHOICE_LABELS["frequency"]), required=False, allow_blank=True
    )
    audience = serializers.ChoiceField(
        choices=list(CHOICE_LABELS["audience"]), required=False, allow_blank=True
    )
    record_link = serializers.URLField(
        max_length=2000, required=False, allow_blank=True
    )

    def validate(self, attrs):
        fields = REQUEST_FIELDS[attrs["category"]]
        missing = {
            key: f"Complete: {label}."
            for key, label, required in fields
            if required and not attrs.get(key)
        }
        if attrs["category"] == "help":
            # A question is enough; customers should not have to repeat it as a subject.
            attrs["subject"] = " ".join(attrs.get("question", "").split())[:160]
        elif not attrs.get("subject"):
            missing["subject"] = "Add a short title."
        if missing:
            raise serializers.ValidationError(missing)
        return {
            key: value
            for key, value in attrs.items()
            if key
            in {"request_id", "category", "area", "subject"}
            | {key for key, _, _ in fields}
        }

    def validate_subject(self, value):
        return " ".join(value.split())


class HelpRequestView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)
    throttle_classes = (SupportThrottle,)

    def get(self, request):
        return Response(
            {
                "recipient": SUPPORT_EMAIL,
                "reply_to": request.user.email,
                "name": request.user.name or request.user.email,
                "organization": request.profile.org.name,
                "delivery_mode": delivery_mode(),
                "areas": AREAS,
            },
            headers={"Cache-Control": "private, no-store"},
        )

    def post(self, request):
        serializer = SupportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        mode = delivery_mode()
        if mode == "unavailable":
            return Response(
                {
                    "detail": "Support email is not configured. Email info@highdemandmedia.com directly."
                },
                status=503,
            )
        key = f"crm-support:{request.profile.org_id}:{request.user.pk}:{values['request_id']}"
        fingerprint = hashlib.sha256(
            json.dumps(values, sort_keys=True, default=str).encode()
        ).hexdigest()
        saved = cache.get(key)
        if saved:
            if saved["fingerprint"] != fingerprint:
                return Response(
                    {"detail": "This request was already sent. Start a new request."},
                    status=409,
                )
            return Response(saved["response"])
        lock = key + ":sending"
        if not cache.add(lock, True, timeout=60):
            return Response(
                {
                    "detail": "This request is being sent. Please wait before trying again."
                },
                status=409,
            )
        try:
            # A concurrent sender may have finished between the first read and lock.
            saved = cache.get(key)
            if saved:
                if saved["fingerprint"] != fingerprint:
                    return Response(
                        {
                            "detail": "This request was already sent. Start a new request."
                        },
                        status=409,
                    )
                return Response(saved["response"])
            reference = "HDM-" + uuid.uuid4().hex[:12].upper()
            body = "\n".join(
                [
                    f"Reference: {reference}",
                    f"Type: {CATEGORIES[values['category']]}",
                    f"Area: {values['area']}",
                    f"Subject: {values['subject']}",
                    f"From: {request.user.name or request.user.email} <{request.user.email}>",
                    f"Organization: {request.profile.org.name}",
                    f"Organization ID: {request.profile.org_id}",
                    *[
                        part
                        for key, label, _ in REQUEST_FIELDS[values["category"]]
                        if values.get(key)
                        for part in (
                            "",
                            label,
                            CHOICE_LABELS.get(key, {}).get(values[key], values[key]),
                        )
                    ],
                ]
            )
            message = EmailMessage(
                subject=f"[HDM CRM · {CATEGORIES[values['category']]}] {values['subject']}",
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[SUPPORT_EMAIL],
                reply_to=[request.user.email],
                headers={"X-HDM-Support-Reference": reference},
            )
            try:
                sent = message.send(fail_silently=False)
            except Exception:
                logger.exception("CRM support email delivery failed")
                return Response(
                    {
                        "detail": "Your request could not be sent. Your text is preserved; please try again or email info@highdemandmedia.com."
                    },
                    status=503,
                )
            if sent != 1:
                return Response(
                    {
                        "detail": "The email service did not accept this request. Please try again."
                    },
                    status=503,
                )
            result = {
                "reference": reference,
                "delivery_mode": mode,
                "recipient": SUPPORT_EMAIL,
            }
            cache.set(
                key, {"fingerprint": fingerprint, "response": result}, timeout=86400
            )
            return Response(result, status=status.HTTP_201_CREATED)
        finally:
            cache.delete(lock)
