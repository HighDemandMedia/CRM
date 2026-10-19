"""Single-use password reset: no login grant and no account enumeration."""

import hashlib
import logging

from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import User
from common.password_reset import (
    queue_reset_notice,
    revoke_user_sessions,
    send_password_reset_email,
)
from common.views.password_auth_views import (
    PasswordIdentityThrottle,
    PasswordIPThrottle,
    check_new_password,
)

logger = logging.getLogger(__name__)

INVALID_LINK = "This reset link is invalid or expired. Request a new one."


class ResetIdentityThrottle(PasswordIdentityThrottle):
    scope = "password_reset_identity"
    rate = "5/hour"

    def get_cache_key(self, request, view):
        # Confirmation identifies the account by uid, never by the secret token.
        identity = (
            str(request.data.get("email") or request.data.get("uid") or "")
            .strip()
            .casefold()
        )
        return self.cache_format % {
            "scope": self.scope,
            "ident": hashlib.sha256(identity.encode()).hexdigest(),
        }


class ResetRequestInput(serializers.Serializer):
    email = serializers.EmailField()
    language = serializers.ChoiceField(choices=["en", "es"], default="en")


class ResetConfirmInput(serializers.Serializer):
    uid = serializers.CharField(max_length=128)
    token = serializers.CharField(max_length=128)
    password = serializers.CharField(
        min_length=10, max_length=128, trim_whitespace=False, write_only=True
    )
    password_confirm = serializers.CharField(
        max_length=128, trim_whitespace=False, write_only=True
    )
    language = serializers.ChoiceField(choices=["en", "es"], default="en")

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs


class PasswordResetRequestView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [PasswordIPThrottle, ResetIdentityThrottle]

    def post(self, request):
        data = ResetRequestInput(data=request.data)
        data.is_valid(raise_exception=True)
        # Queue even unknown addresses so account lookup and mail delivery do not
        # affect the public response or its timing.
        try:
            send_password_reset_email.delay(**data.validated_data)
        except Exception:
            logger.error("Password reset request could not be queued", exc_info=False)
            return Response(
                {"error": "Email could not be sent. Please try again shortly."},
                status=503,
            )
        return Response(
            {"message": "If the account is eligible, a reset link will be sent."}
        )


class PasswordResetConfirmView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [PasswordIPThrottle, ResetIdentityThrottle]

    @transaction.atomic
    def post(self, request):
        data = ResetConfirmInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        try:
            uid = urlsafe_base64_decode(values["uid"]).decode()
            user = User.objects.select_for_update().get(pk=uid, is_active=True)
        except (User.DoesNotExist, ValueError, UnicodeError, ValidationError):
            return Response({"error": INVALID_LINK}, status=400)
        if not default_token_generator.check_token(user, values["token"]):
            return Response({"error": INVALID_LINK}, status=400)
        check_new_password(values["password"], user)
        user.set_password(values["password"])
        user.save(update_fields=["password"])
        revoke_user_sessions(user)
        transaction.on_commit(lambda: queue_reset_notice(user.pk, values["language"]))
        return Response(
            {"message": "Password updated. Sign in with your new password."}
        )
