from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.audit_log import SecurityAuditLog
from common.models import CRMRole, Org, Profile
from common.permissions import HasOrgContext, IsOrgAdmin
from common.rbac import (
    ACTION_LABELS,
    ACTIONS,
    BOOLEAN_ACTIONS,
    MODULE_LABELS,
    MODULES,
    SCHEMA,
    SCOPES,
    default_rules,
    ensure_default_roles,
    expanded_rules,
    scope_for,
    validate_rules,
)
from common.settings_access import settings_access, validate_settings_access


class RoleInput(serializers.Serializer):
    scope = serializers.ChoiceField(
        choices=["own", "team", "organization"], required=False
    )
    name = serializers.CharField(max_length=80)
    description = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    rules = serializers.JSONField()
    settings_access = serializers.JSONField(required=False)

    def validate_settings_access(self, value):
        return validate_settings_access(value)

    def validate_rules(self, value):
        return validate_rules(value)

    def validate(self, attrs):
        enabled = {
            value
            for row in attrs["rules"].values()
            for action, value in row.items()
            if action not in BOOLEAN_ACTIONS and value != "none"
        }
        scope = attrs.get("scope")
        if scope is None:
            if len(enabled) > 1:
                raise serializers.ValidationError(
                    "Choose one scope for this permission set."
                )
            scope = next(iter(enabled), "own")
        fixed = {"Member": "own", "Manager": "team"}.get(attrs["name"])
        if fixed and scope != fixed:
            raise serializers.ValidationError(
                "Member uses Personal; Manager uses Team."
            )
        if enabled - {scope}:
            raise serializers.ValidationError(
                "All enabled permissions must use the selected scope."
            )
        grants = attrs.get("settings_access", {})
        if attrs["name"] != "Manager" and any(v != "none" for v in grants.values()):
            raise serializers.ValidationError(
                {
                    "settings_access": "Only the Manager permission set can receive Settings access."
                }
            )
        attrs["scope"] = scope
        return attrs

    def validate_name(self, value):
        if value.casefold().replace("_", " ") in ("admin", "super admin"):
            raise serializers.ValidationError(
                "Admin and Super Admin are protected system roles."
            )
        return value


def role_data(role):
    return {
        "id": str(role.pk),
        "name": role.name,
        "scope": role.scope,
        "description": role.description,
        "settings_access": role.settings_access,
        "rules": expanded_rules(
            role.rules, role.scope, role.name in ("Member", "Manager")
        ),
        "member_count": role.members.filter(removed_at__isnull=True).count(),
    }


class RolesView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext, IsOrgAdmin]

    def get(self, request):
        ensure_default_roles(request.org)
        return Response(
            {
                "roles": [
                    role_data(role)
                    for role in CRMRole.objects.filter(org=request.org).order_by("name")
                ],
                "modules": MODULES,
                "actions": ACTIONS,
                "scopes": SCOPES,
                "catalog": [
                    {
                        "key": key,
                        "label": MODULE_LABELS[key],
                        "actions": [
                            {
                                "key": action,
                                "label": (
                                    "Reschedule"
                                    if key == "calendar" and action == "edit"
                                    else "Choose another host"
                                    if key == "calendar" and action == "reassign"
                                    else ACTION_LABELS[action]
                                ),
                                "boolean": action in BOOLEAN_ACTIONS,
                            }
                            for action in SCHEMA[key]
                        ],
                    }
                    for key in MODULES
                ],
            }
        )

    @transaction.atomic
    def post(self, request):
        data = RoleInput(data=request.data)
        data.is_valid(raise_exception=True)
        Org.objects.select_for_update().get(pk=request.org.pk)
        if CRMRole.objects.filter(
            org=request.org, name__iexact=data.validated_data["name"]
        ).exists():
            return Response(
                {"error": "A role with this name already exists."}, status=400
            )
        role = CRMRole.objects.create(org=request.org, **data.validated_data)
        SecurityAuditLog.objects.create(
            event_type="PERMISSION_SET_CHANGED",
            user=request.user,
            org=request.org,
            description="Permission set created",
            metadata={"role_id": str(role.pk), "after": role_data(role)},
        )
        return Response(role_data(role), status=201)


class RoleDetailView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext, IsOrgAdmin]

    @transaction.atomic
    def patch(self, request, pk):
        role = get_object_or_404(
            CRMRole.objects.select_for_update(), pk=pk, org=request.org
        )
        data = RoleInput(data=request.data)
        data.is_valid(raise_exception=True)
        if (
            role.name in ("Member", "Manager")
            and data.validated_data["name"] != role.name
        ):
            return Response(
                {
                    "error": "Keep the default role name; its permissions remain editable."
                },
                status=400,
            )
        if (
            CRMRole.objects.filter(
                org=request.org, name__iexact=data.validated_data["name"]
            )
            .exclude(pk=pk)
            .exists()
        ):
            return Response(
                {"error": "A role with this name already exists."}, status=400
            )
        before = role_data(role)
        for key, value in data.validated_data.items():
            setattr(role, key, value)
        role.save()
        SecurityAuditLog.objects.create(
            event_type="PERMISSION_SET_CHANGED",
            user=request.user,
            org=request.org,
            description="Permission set updated",
            metadata={
                "role_id": str(role.pk),
                "before": before,
                "after": role_data(role),
            },
        )
        return Response(role_data(role))


class MemberRoleView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext, IsOrgAdmin]

    @transaction.atomic
    def post(self, request, pk):
        Org.objects.select_for_update().get(pk=request.org.pk)
        member = get_object_or_404(
            Profile.objects.select_for_update(),
            pk=pk,
            org=request.org,
            removed_at__isnull=True,
        )
        if member.is_super_admin:
            return Response(
                {
                    "error": "Super Admin belongs to the organization creator and cannot be reassigned."
                },
                status=403,
            )
        if member.pk == request.profile.pk:
            return Response(
                {"error": "You cannot change your own access role."}, status=400
            )
        value = request.data.get("role_id")
        from common.member_access import assert_member_management

        assert_member_management(request.profile, member, value)
        if value == "ADMIN":
            role = None
        else:
            value = serializers.UUIDField().run_validation(value)
            role = get_object_or_404(CRMRole, pk=value, org=request.org)
        if (
            member.role == "ADMIN"
            and role
            and not Profile.objects.filter(
                org=request.org, role="ADMIN", is_active=True
            )
            .exclude(pk=member.pk)
            .exists()
        ):
            return Response(
                {"error": "Keep at least one active administrator."}, status=400
            )
        member.role = "ADMIN" if role is None else "USER"
        member.access_role = role
        member.save()
        return Response({"saved": True})


class RoleExportCheckView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request, module):
        from common.rbac import MODULES, require

        if module not in MODULES:
            return Response(status=404)
        require(request.profile, module, "export")
        return Response({"allowed": True})


def permissions_payload(profile):
    """Fresh permissions shared by the standalone endpoint and UI bootstrap."""
    from common.rbac import calendar_hosts, configured

    rules = (
        {
            module: {action: scope_for(profile, module, action) for action in actions}
            for module, actions in SCHEMA.items()
        }
        if profile.role == "ADMIN" or configured(profile)
        else default_rules()
    )
    return {
        "rules": rules,
        "is_admin": profile.role == "ADMIN",
        "settings_access": settings_access(profile),
        "calendar_host_ids": list(calendar_hosts(profile).values_list("pk", flat=True)),
    }


class MyPermissionsView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request):
        return Response(
            permissions_payload(request.profile),
            headers={"Cache-Control": "private, no-store"},
        )
