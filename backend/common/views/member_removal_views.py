from django.apps import apps
from django.core import signing
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.member_access import assert_member_management
from common.models import Org, OrganizationInvitation, PersonalAccessToken, Profile
from common.permissions import HasOrgContext, IsOrgAdmin

RECORDS = {
    "contacts.contact": "Contacts",
    "accounts.account": "Companies",
    "opportunity.opportunity": "Deals",
    "tasks.task": "Tasks",
    "cases.case": "Tickets",
}


class RemovalInput(serializers.Serializer):
    token = serializers.CharField()
    confirmation = serializers.CharField(trim_whitespace=False)
    reassign_to = serializers.UUIDField(required=False, allow_null=True)


class MemberRemovalView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext, IsOrgAdmin]

    def target(self, request, pk):
        member = get_object_or_404(
            Profile.objects.select_related("user", "org"),
            pk=pk,
            org=request.org,
            removed_at__isnull=True,
        )
        assert_member_management(request.profile, member)
        return member

    def rows(self, member):
        return {
            label: apps.get_model(model)
            .objects.filter(org_id=member.org_id, assigned_to=member)
            .distinct()
            for model, label in RECORDS.items()
        }

    def get(self, request, pk):
        member = self.target(request, pk)
        counts = {label: rows.count() for label, rows in self.rows(member).items()}
        token = signing.dumps(
            {
                "member": str(member.pk),
                "org": str(request.org.pk),
                "actor": str(request.profile.pk),
                "email": member.user.email,
                "counts": counts,
            },
            salt="member-removal",
        )
        candidates = (
            Profile.objects.filter(
                org=request.org, is_active=True, removed_at__isnull=True
            )
            .exclude(pk=member.pk)
            .select_related("user")
        )
        return Response(
            {
                "email": member.user.email,
                "name": member.user.name or member.user.email,
                "counts": counts,
                "token": token,
                "candidates": [
                    {
                        "id": str(p.pk),
                        "name": p.user.name or p.user.email,
                        "email": p.user.email,
                    }
                    for p in candidates
                ],
            }
        )

    @transaction.atomic
    def post(self, request, pk):
        data = RemovalInput(data=request.data)
        data.is_valid(raise_exception=True)
        Org.objects.select_for_update().get(pk=request.org.pk)
        Profile.objects.select_for_update().filter(pk=pk, org=request.org).first()
        member = self.target(request, pk)
        try:
            preview = signing.loads(
                data.validated_data["token"], salt="member-removal", max_age=900
            )
        except signing.BadSignature:
            raise serializers.ValidationError(
                "Confirmation expired. Close and reopen this dialog."
            )
        expected = {
            "member": str(member.pk),
            "org": str(request.org.pk),
            "actor": str(request.profile.pk),
            "email": member.user.email,
        }
        if (
            any(preview.get(key) != value for key, value in expected.items())
            or data.validated_data["confirmation"] != member.user.email
        ):
            raise serializers.ValidationError(
                "Type the user email exactly to confirm removal."
            )
        destination = None
        if data.validated_data.get("reassign_to"):
            destination = get_object_or_404(
                Profile.objects.select_for_update(),
                pk=data.validated_data["reassign_to"],
                org=request.org,
                is_active=True,
                removed_at__isnull=True,
            )
            if destination.pk == member.pk:
                raise serializers.ValidationError("Choose another active user.")
        rows = self.rows(member)
        if preview.get("counts") != {
            label: query.count() for label, query in rows.items()
        }:
            return Response(
                {
                    "message": "Assignments changed. Close and reopen this dialog to review them."
                },
                status=409,
            )
        for query in rows.values():
            for record in query:
                if destination:
                    record.assigned_to.add(destination)
                record.assigned_to.remove(member)
        member.user_teams.clear()
        apps.get_model("tasks", "BoardMember").objects.filter(
            org=request.org, profile=member
        ).delete()
        member.is_active = False
        member.removed_at = timezone.now()
        member.save()
        PersonalAccessToken.objects.filter(
            profile=member, revoked_at__isnull=True
        ).update(revoked_at=timezone.now())
        OrganizationInvitation.objects.filter(
            org=request.org,
            email__iexact=member.user.email,
            accepted_at__isnull=True,
            revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())
        from common.audit_log import AuditLogger

        AuditLogger()._log(
            "MEMBERSHIP_REVOKED",
            user=request.user,
            org=request.org,
            description="User removed from organization",
            metadata={
                "profile_id": str(member.pk),
                "reassigned_to": str(destination.pk) if destination else None,
                "records": preview["counts"],
            },
            request=request,
        )
        return Response({"removed": True})
