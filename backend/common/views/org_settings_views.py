from django.db import transaction
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import Profile
from common.org_time import selectable_timezones
from common.permissions import HasOrgContext
from common.serializer import OrgSettingsSerializer
from common.settings_access import HasSettingsAccess, can_access_settings


class OrgSettingsView(APIView):
    """
    API endpoint for org settings (currency, country, locale).

    GET: Returns current org settings
    PATCH: Updates org settings (requires Organization management)
    """

    settings_section = "organization"
    permission_classes = (IsAuthenticated, HasOrgContext, HasSettingsAccess)

    def get(self, request):
        """Get current organization settings."""
        if not request.profile:
            return Response(
                {"error": "Organization context required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        org = request.profile.org
        serializer = OrgSettingsSerializer(org, context={"request": request})
        return Response(
            {
                **serializer.data,
                "is_super_admin": request.profile.is_super_admin,
                "setup_step": request.profile.setup_step,
            }
        )

    @transaction.atomic
    def patch(self, request):
        """Update organization settings (requires Organization management)."""
        if not request.profile:
            return Response(
                {"error": "Organization context required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not can_access_settings(request.profile, "organization", manage=True):
            return Response(
                {"error": "Organization management permission required"},
                status=status.HTTP_403_FORBIDDEN,
            )

        completing = serializers.BooleanField().run_validation(
            request.data.get("complete_setup", False)
        )
        if completing and request.profile.setup_step in (
            Profile.SetupStep.PROFILE,
            Profile.SetupStep.PROFILE_ORGANIZATION,
        ):
            raise serializers.ValidationError({"error": "Complete your profile first."})
        org = request.profile.org
        serializer = OrgSettingsSerializer(
            org, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            if completing:
                missing = {
                    field: "Confirm this field before continuing."
                    for field in ("name", "default_currency", "timezone")
                    if not serializer.validated_data.get(field)
                }
                if missing:
                    raise serializers.ValidationError(missing)
            serializer.save()
            if (
                completing
                and request.profile.setup_step == Profile.SetupStep.ORGANIZATION
            ):
                request.profile.setup_step = Profile.SetupStep.COMPLETE
                request.profile.save(update_fields=["setup_step"])
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TimezoneListView(APIView):
    """The zone names a client may offer when creating or editing an org.

    Served rather than built client-side because the two clients would not
    otherwise agree: a browser's ``Intl.supportedValuesOf('timeZone')`` answers
    "Asia/Calcutta" where this database also knows "Asia/Kolkata", and a select
    that cannot find the stored value submits its first option instead. See
    ``common.org_time.selectable_timezones``.

    Each entry carries the zone's current UTC offset so a client can preselect a
    sensible default. Mobile cannot read the device's IANA name without a
    platform package, but it can always read the device's offset.

    Authenticated but deliberately org-free: the first caller is a user creating
    their very first organization, who has no org claim yet. The list is the same
    for every tenant and contains no tenant data, so there is nothing here to
    scope.
    """

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=["organization"],
        operation_id="timezone_list",
        responses={
            200: inline_serializer(
                name="TimezoneListResponse",
                fields={
                    "timezones": serializers.ListField(
                        child=inline_serializer(
                            name="TimezoneOption",
                            fields={
                                "name": serializers.CharField(),
                                "offset_minutes": serializers.IntegerField(),
                            },
                        )
                    )
                },
            )
        },
    )
    def get(self, request):
        return Response({"timezones": selectable_timezones()})
