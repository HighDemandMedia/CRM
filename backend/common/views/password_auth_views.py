"""Personal password access; organization membership remains the access boundary."""

import hashlib

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from common.audit_log import audit_log
from common.models import OrganizationInvitation, Profile, User
from common.platform_access import accessible_profiles
from common.rbac import ensure_default_roles
from common.serializer import OrgAwareRefreshToken, OrgProfileCreateSerializer
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
            "ident": self.get_ident(request),
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


def session_response(user, request, status=200):
    profiles = list(
        accessible_profiles(user).select_related("org").order_by("org__name")
    )
    profile = profiles[0] if len(profiles) == 1 else None
    if request.auth and request.auth.get("org_id"):
        profile = next(
            (p for p in profiles if str(p.org_id) == request.auth["org_id"]), profile
        )
    org = profile.org if profile else None
    token = OrgAwareRefreshToken.for_user_and_org(user, org, profile)
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
        return session_response(user, request)


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
                    accepted_at__isnull=True,
                    revoked_at__isnull=True,
                    expires_at__gt=timezone.now(),
                    org__is_active=True,
                )
                .first()
            )
        if not invitation:
            return Response(
                {
                    "error": "This invitation is invalid, expired, cancelled, or already accepted. Ask your administrator for a new invitation."
                },
                status=400,
                headers={"Cache-Control": "no-store"},
            )
        return Response(
            {
                "email": invitation.email,
                "organization": invitation.org.name,
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
    def post(self, request):
        if not getattr(
            settings, "PASSWORD_REGISTRATION_ENABLED", True
        ) and not request.data.get("invitation"):
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
            with transaction.atomic():
                invitation = None
                if values.get("invitation"):
                    invitation = (
                        OrganizationInvitation.objects.select_for_update()
                        .select_related("org")
                        .filter(
                            token_hash=digest(values["invitation"]),
                            email__iexact=values["email"],
                            accepted_at__isnull=True,
                            revoked_at__isnull=True,
                            expires_at__gt=timezone.now(),
                            org__is_active=True,
                        )
                        .first()
                    )
                    if not invitation:
                        return Response(
                            {
                                "error": "Invitation is invalid, expired, or belongs to another email."
                            },
                            status=400,
                        )
                org_data = None
                if not invitation:
                    org_data = OrgProfileCreateSerializer(
                        data={
                            "name": values["organization"],
                            "timezone": values["timezone"],
                        }
                    )
                    org_data.is_valid(raise_exception=True)
                user = User.objects.create_user(
                    values["email"], values["password"], name=values["name"]
                )
                org = invitation.org if invitation else org_data.save(created_by=user)
                # Default roles are tenant tables protected by FORCE RLS.
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT set_config('app.current_org', %s, true)",
                            [str(org.pk)],
                        )
                defaults = ensure_default_roles(org)
                Profile.objects.create(
                    user=user,
                    org=org,
                    role=invitation.role if invitation else "ADMIN",
                    access_role=(invitation.access_role or defaults[0])
                    if invitation and invitation.role != "ADMIN"
                    else None,
                    is_active=True,
                )
                if invitation:
                    invitation.accepted_at = timezone.now()
                    invitation.save(update_fields=["accepted_at"])
                return session_response(user, request, status=201)
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
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)
        return session_response(user, request)
