"""Personal password access; organization membership remains the access boundary."""

import hashlib

from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.audit_log import audit_log
from common.invitation_registration import register_invited_user
from common.invitation_status import invitation_issue
from common.legal import (
    legal_requirements,
)
from common.models import OrganizationInvitation, User
from common.organization_lifecycle import invitation_write
from common.password_reset import revoke_user_sessions
from common.platform_access import accessible_profiles
from common.request_meta import client_ip
from common.serializer import OrgAwareRefreshToken
from common.views.auth_views import _org_payload
from common.views.invitation_views import digest


class PasswordIPThrottle(SimpleRateThrottle):
    scope = "password_ip"
    rate = "30/hour"

    def get_cache_key(self, request, view):
        if request.method != "POST":
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": client_ip(request) or "unknown",
        }


class PasswordIdentityThrottle(PasswordIPThrottle):
    scope = "password_identity"
    rate = "10/hour"

    def get_cache_key(self, request, view):
        if request.method != "POST":
            return None
        identity = (
            str(request.data.get("email", request.user.pk or "")).strip().casefold()
        )
        key = hashlib.sha256(identity.encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": key}


class RegistrationThrottle(PasswordIPThrottle):
    scope = "password_registration"
    rate = "5/hour"


class LoginInput(serializers.Serializer):
    remember_me = serializers.BooleanField(default=False)
    email = serializers.EmailField()
    password = serializers.CharField(
        trim_whitespace=False, max_length=128, write_only=True
    )


def check_new_password(password, user):
    try:
        validate_password(password, user)
    except ValidationError as exc:
        raise serializers.ValidationError({"password": exc.messages}) from exc


class RegisterInput(LoginInput):
    name = serializers.CharField(max_length=255)
    organization = serializers.CharField(max_length=255, required=False)
    invitation = serializers.CharField(max_length=128, required=False)
    timezone = serializers.CharField(max_length=64, default="UTC")
    password = serializers.CharField(
        min_length=10, max_length=128, trim_whitespace=False, write_only=True
    )

    def validate(self, attrs):
        attrs["email"] = attrs["email"].lower()
        check_new_password(
            attrs["password"], User(email=attrs["email"], name=attrs["name"])
        )
        if not attrs.get("invitation") and not attrs.get("organization"):
            raise serializers.ValidationError(
                {"organization": "Organization name is required."}
            )
        return attrs


def session_response(
    user, request, status=200, *, remember_me=False, organization_id=None
):
    profiles = list(
        accessible_profiles(user).select_related("org").order_by("org__name")
    )
    profile = profiles[0] if len(profiles) == 1 else None
    from common.identifiers import resolve_identifier

    if request.auth and request.auth.get("org_id"):
        selected_org = resolve_identifier(request.auth["org_id"])
        profile = next((p for p in profiles if str(p.org_id) == selected_org), profile)
    if organization_id is not None:
        organization_id = resolve_identifier(organization_id)
        profile = next(
            (p for p in profiles if str(p.org_id) == str(organization_id)), None
        )
    org = profile.org if profile else None
    token = OrgAwareRefreshToken.for_user_and_org(
        user, org, profile, remember_me=remember_me, session=request.auth
    )
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
    audit_log.login_success(user, org, request)
    return Response(
        {
            "access_token": str(token.access_token),
            "refresh_token": str(token),
            "current_org": _org_payload(org) if org else None,
            "organizations": [_org_payload(p.org, role=p.role) for p in profiles],
        },
        status=status,
    )


class PasswordLoginView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [PasswordIPThrottle, PasswordIdentityThrottle]

    @extend_schema(tags=["auth"], request=LoginInput)
    def post(self, request):
        data = LoginInput(data=request.data)
        data.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=data.validated_data["email"]).first()
        password = data.validated_data["password"]
        valid = user.check_password(password) if user else False
        if not user:
            make_password(password)  # Avoid a fast response for unknown addresses.
        if not valid or not user.is_active:
            return Response(
                {"error": "Email or password is incorrect, or access is disabled."},
                status=401,
            )
        return session_response(
            user, request, remember_me=data.validated_data["remember_me"]
        )


class InvitationPreviewView(APIView):
    """Expose onboarding details only to the holder of a valid invitation."""

    authentication_classes = []
    permission_classes = []
    throttle_classes = [PasswordIPThrottle]

    def post(self, request):
        raw = request.data.get("token")
        invitation = None
        if isinstance(raw, str) and 20 <= len(raw) <= 128:
            invitation = (
                OrganizationInvitation.objects.select_related("org")
                .filter(
                    token_hash=digest(raw),
                    org__is_active=True,
                )
                .first()
            )
        issue = invitation_issue(invitation)
        if issue:
            code, message = issue
            return Response(
                {"code": code, "error": message},
                status=400,
                headers={"Cache-Control": "no-store"},
            )
        return Response(
            {
                "email": invitation.email,
                "organization": invitation.org.name,
                "legal": legal_requirements(invitation),
                "existing_account": User.objects.filter(
                    email__iexact=invitation.email
                ).exists(),
            },
            headers={"Cache-Control": "no-store"},
        )


class PasswordRegisterView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [RegistrationThrottle]

    @extend_schema(tags=["auth"], request=RegisterInput)
    @invitation_write
    def post(self, request):
        if not request.data.get("invitation"):
            return Response(
                {"error": "Account registration is currently closed."}, status=403
            )
        data = RegisterInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        duplicate = {
            "error": "This email cannot be registered. Sign in or use email recovery."
        }
        if User.objects.filter(email__iexact=values["email"]).exists():
            return Response(duplicate, status=400)
        try:
            user, invitation = register_invited_user(
                token=values.get("invitation"),
                email=values["email"],
                name=values["name"],
                password=values["password"],
                legal_data=request.data,
            )
            response = session_response(
                user, request, status=201, organization_id=invitation.org_id
            )
            response.data["needs_organization_setup"] = invitation.grants_ownership
            return response
        except IntegrityError:
            return Response(duplicate, status=400)


class ChangePasswordInput(serializers.Serializer):
    current_password = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=False,
        max_length=128,
        write_only=True,
    )
    password = serializers.CharField(
        min_length=10, max_length=128, trim_whitespace=False, write_only=True
    )


class PasswordChangeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [PasswordIPThrottle, PasswordIdentityThrottle]

    def get(self, request):
        return Response(
            {
                "has_password": request.user.has_usable_password(),
                "can_reset_password": request.auth.get("password_reset_until", 0)
                > timezone.now().timestamp(),
            }
        )

    @extend_schema(tags=["auth"], request=ChangePasswordInput)
    @transaction.atomic
    def post(self, request):
        data = ChangePasswordInput(data=request.data)
        data.is_valid(raise_exception=True)
        user = User.objects.select_for_update().get(pk=request.user.pk)
        if (
            user.has_usable_password()
            and request.auth.get("password_reset_until", 0)
            <= timezone.now().timestamp()
            and not user.check_password(data.validated_data.get("current_password", ""))
        ):
            return Response({"error": "Current password is incorrect."}, status=400)
        password = data.validated_data["password"]
        check_new_password(password, user)
        user.set_password(password)
        user.save(update_fields=["password"])
        revoke_user_sessions(user)
        return session_response(user, request)
