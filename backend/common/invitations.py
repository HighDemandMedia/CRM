"""Invitation delivery and the owner-authorized initial tenant handoff."""

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from rest_framework.exceptions import ValidationError

from common.models import Org


def send_invitation(row, raw, *, sender=send_mail):
    link = f"{settings.FRONTEND_URL.rstrip('/')}/invite?token={raw}"
    sent = sender(
        f"Invitation to {row.org.name} · High Demand Media CRM",
        f"You have been invited to {row.org.name}.\n\nOpen this link to join:\n{link}\n\nIf you are new to High Demand Media CRM, you will create your own password for {row.email}. If you already have an account, sign in with that email to accept.\n\nThis invitation expires in 7 days. If you were not expecting it, you can ignore this email.",
        settings.DEFAULT_FROM_EMAIL,
        [row.email],
        fail_silently=False,
        html_message=render_to_string(
            "emails/invitation.html",
            {"organization": row.org.name, "email": row.email, "link": link},
        ),
    )

    if sent == 0:
        raise RuntimeError("Invitation email was not accepted by the mail backend.")
    return sent


def accept_ownership(invitation, user):
    # Called inside acceptance's transaction. Only the platform owner's initial
    # invitation can hand off ownership; ordinary team invitations never can.
    if not invitation.grants_ownership:
        return
    org = Org.objects.select_for_update().get(pk=invitation.org_id)
    if (
        invitation.role != "ADMIN"
        or not invitation.invited_by_id
        or not invitation.invited_by.is_active
        or not invitation.invited_by.is_superuser
        or org.owner_id != invitation.invited_by_id
    ):
        raise ValidationError(
            "This administrator invitation is no longer valid. Contact High Demand Media."
        )
    Org.objects.filter(pk=org.pk, owner_id=invitation.invited_by_id).update(owner=user)
    invitation.org.owner_id = user.pk
