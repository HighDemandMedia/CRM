"""Invitation delivery and the owner-authorized initial tenant handoff."""

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from rest_framework.exceptions import ValidationError

from common.models import Org, Profile


def send_invitation(row, raw, *, sender=send_mail):
    link = f"{settings.FRONTEND_URL.rstrip('/')}/invite?token={raw}"
    owner = row.grants_ownership
    heading = "Congratulations — welcome to your CRM!" if owner else "Join your team"
    introduction = (
        "Welcome to your specialized CRM, developed by High Demand Media. "
        "Your workspace is ready to bring your contacts, sales opportunities "
        "and follow-ups together, with support from the HDM team."
        if owner
        else f"You have been invited to {row.org.name} in High Demand Media CRM."
    )
    button_label = "Activate your account" if owner else "Accept invitation"
    setup_message = (
        "Next, complete your profile and your organization's information and settings."
        if owner
        else "Next, complete your profile and preferences to join your team."
    )
    sent = sender(
        "Welcome to your CRM · High Demand Media"
        if owner
        else f"Invitation to {row.org.name} · High Demand Media CRM",
        f"{heading}\n\n{introduction}\n\nWorkspace: {row.org.name}\n\n{button_label}:\n{link}\n\nContinue with Google using {row.email}, or create your own password. If you already have an account, sign in with that email to accept.\n\n{setup_message}\n\nThis invitation expires in 7 days. If you were not expecting it, you can ignore this email.",
        settings.DEFAULT_FROM_EMAIL,
        [row.email],
        fail_silently=False,
        html_message=render_to_string(
            "emails/invitation.html",
            {
                "organization": row.org.name,
                "email": row.email,
                "link": link,
                "setup_message": setup_message,
                "heading": heading,
                "introduction": introduction,
                "button_label": button_label,
                "grants_ownership": owner,
            },
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
    # Also normalize invitations created before provisioning distinguished
    # platform access from customer membership. Preserve the profile for audit FKs.
    Profile.objects.filter(org=org, user_id=invitation.invited_by_id).update(
        is_platform_access=True
    )
    invitation.org.owner_id = user.pk
