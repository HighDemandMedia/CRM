import hashlib
import secrets
from datetime import timedelta

from django.core.mail import send_mail
from django.db import connection, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.invitations import accept_ownership, send_invitation
from common.models import CRMRole, Org, OrganizationInvitation, Profile
from common.permissions import HasOrgContext, IsOrgAdmin
from common.rbac import ensure_default_roles


class InviteInput(serializers.Serializer):
    email = serializers.EmailField()
    access_role_id = serializers.UUIDField(required=False, allow_null=True)
    role = serializers.ChoiceField(choices=["ADMIN", "USER"], default="USER")


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def invitation_data(row):
    return {
        "id": str(row.pk),
        "email": row.email,
        "role": row.role,
        "created_at": row.created_at,
        "access_role_id": str(row.access_role_id) if row.access_role_id else None,
        "access_role_name": row.access_role.name if row.access_role_id else None,
        "expires_at": row.expires_at,
        "status": "Accepted"
        if row.accepted_at
        else "Cancelled"
        if row.revoked_at
        else "Expired"
        if row.expires_at <= timezone.now()
        else "Pending",
    }


class InvitationsView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext, IsOrgAdmin]

    def get(self, request):
        rows = OrganizationInvitation.objects.filter(org=request.profile.org).order_by(
            "-created_at"
        )
        return Response({"invitations": [invitation_data(row) for row in rows]})

    def post(self, request):
        return create_invitation(request)


def create_invitation(request):
    data = InviteInput(data=request.data)
    data.is_valid(raise_exception=True)
    from common.member_access import assert_member_management

    assert_member_management(request.profile, new_role=data.validated_data["role"])
    email = data.validated_data["email"].strip().lower()
    access_role = None
    if data.validated_data["role"] != "ADMIN":
        role_id = data.validated_data.get("access_role_id")
        access_role = (
            get_object_or_404(CRMRole, pk=role_id, org=request.org)
            if role_id
            else ensure_default_roles(request.org)[0]
        )
    raw = secrets.token_urlsafe(32)
    with transaction.atomic():
        # Lock the organization so simultaneous invites cannot create two grants.
        org = Org.objects.select_for_update().get(pk=request.profile.org_id)
        if Profile.objects.filter(
            org=org, user__email__iexact=email, removed_at__isnull=True
        ).exists():
            return Response(
                {
                    "error": "This person already belongs to this organization. Manage their access in Users."
                },
                status=400,
            )
        existing = OrganizationInvitation.objects.filter(
            org=org, email=email, accepted_at__isnull=True
        ).first()
        if existing and existing.grants_ownership and not request.user.is_superuser:
            return Response(
                {
                    "error": "Only the platform owner can manage this administrator invitation."
                },
                status=403,
            )
        if (
            existing
            and existing.grants_ownership
            and data.validated_data["role"] != "ADMIN"
        ):
            return Response(
                {
                    "error": "The initial organization invitation must remain an administrator invitation."
                },
                status=400,
            )
        if existing and existing.role == "ADMIN":
            assert_member_management(request.profile, new_role="ADMIN")
        row, _ = OrganizationInvitation.objects.update_or_create(
            org=org,
            email=email,
            defaults={
                "role": data.validated_data["role"],
                "access_role": access_role,
                "token_hash": digest(raw),
                "invited_by": request.user,
                "expires_at": timezone.now() + timedelta(days=7),
                "accepted_at": None,
                "revoked_at": None,
            },
        )
    try:
        send_invitation(row, raw, sender=send_mail)
    except Exception:
        return Response(
            {
                "error": "Invitation saved, but email delivery failed. Use Resend after checking mail settings."
            },
            status=503,
        )
    return Response(invitation_data(row), status=201)


class InvitationDetailView(APIView):
    permission_classes = [IsAuthenticated, HasOrgContext, IsOrgAdmin]

    @transaction.atomic
    def delete(self, request, pk):
        row = get_object_or_404(
            OrganizationInvitation.objects.select_for_update(),
            pk=pk,
            org=request.profile.org,
        )
        from common.member_access import assert_member_management

        assert_member_management(request.profile, new_role=row.role)
        if row.accepted_at:
            return Response(
                {
                    "error": "This invitation was already accepted. Manage the member in Users."
                },
                status=400,
            )
        OrganizationInvitation.objects.filter(
            pk=row.pk, accepted_at__isnull=True
        ).update(revoked_at=timezone.now())
        return Response({"cancelled": True})


class AcceptInvitationView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw = request.data.get("token")
        if not isinstance(raw, str) or not 20 <= len(raw) <= 128:
            return Response({"error": "Invalid invitation."}, status=400)
        with transaction.atomic():
            row = get_object_or_404(
                OrganizationInvitation.objects.select_for_update().select_related(
                    "org"
                ),
                token_hash=digest(raw),
            )
            if row.email.casefold() != request.user.email.casefold():
                return Response(
                    {
                        "error": "Sign in with the email address that received this invitation."
                    },
                    status=403,
                )
            if (
                row.revoked_at
                or row.expires_at <= timezone.now()
                or row.accepted_at
                or not row.org.is_active
            ):
                return Response(
                    {
                        "error": "This invitation has expired, was cancelled, or has already been accepted."
                    },
                    status=400,
                )
            if request.data.get("preview") is True:
                return Response(
                    {"name": row.org.name, "email": row.email, "role": row.role}
                )
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT set_config('app.current_org', %s, true)",
                        [str(row.org_id)],
                    )
            if Profile.objects.filter(
                org=row.org, user=request.user, removed_at__isnull=True
            ).exists():
                return Response(
                    {
                        "error": "Membership already exists. Ask an admin if access is inactive."
                    },
                    status=400,
                )
            Profile.objects.update_or_create(
                org=row.org,
                user=request.user,
                defaults={
                    "role": row.role,
                    "access_role": (row.access_role or ensure_default_roles(row.org)[0])
                    if row.role == "USER"
                    else None,
                    "is_active": True,
                    "removed_at": None,
                    "date_of_joining": timezone.localdate(),
                },
            )
            accept_ownership(row, request.user)
            row.accepted_at = timezone.now()
            row.save(update_fields=["accepted_at"])
        return Response(
            {
                "org_id": str(row.org_id),
                "name": row.org.name,
                "needs_organization_setup": row.grants_ownership,
            }
        )
