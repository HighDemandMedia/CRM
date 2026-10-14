from rest_framework import serializers
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.organization_lifecycle import (
    OWNER_REQUIRED_MESSAGE,
    can_manage_lifecycle,
    change_lifecycle,
    lifecycle_payload,
)
from common.permissions import HasOrgContext


class CanManageOrganizationLifecycle(BasePermission):
    message = OWNER_REQUIRED_MESSAGE

    def has_permission(self, request, view):
        return can_manage_lifecycle(request.org, request.user)


class LifecycleInput(serializers.Serializer):
    action = serializers.ChoiceField(choices=["close", "reactivate"])
    confirmation = serializers.CharField(max_length=100, trim_whitespace=False)


class OrganizationLifecycleView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [
        IsAuthenticated,
        HasOrgContext,
        CanManageOrganizationLifecycle,
    ]

    def post(self, request):
        values = LifecycleInput(data=request.data)
        values.is_valid(raise_exception=True)
        org = change_lifecycle(
            request.org.pk,
            request.user,
            values.validated_data["action"],
            confirmation=values.validated_data["confirmation"],
        )
        return Response(
            lifecycle_payload(org, request.user), headers={"Cache-Control": "no-store"}
        )
