"""Shared delivery checks for queued record-assignment notices."""

from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from common.links import frontend_url
from common.rbac import permitted
from common.tasks import clear_rls_context, set_rls_context


def send_assignment_emails(
    model, record_id, org_id, recipients, *, template, context_key, path, subject
):
    set_rls_context(org_id)
    try:
        record = model.objects.filter(
            pk=record_id, org_id=org_id, is_active=True
        ).first()
        if record is None:
            return
        # A queued job can outlive reassignment, removal or a permission change.
        profiles = record.assigned_to.filter(
            pk__in=recipients,
            org_id=org_id,
            is_active=True,
            removed_at__isnull=True,
            user__is_active=True,
        ).select_related("user", "access_role")
        for profile in profiles:
            if not profile.user.email or not permitted(profile, record):
                continue
            html = render_to_string(
                template,
                {
                    context_key: record,
                    "user": profile.user,
                    "url": frontend_url(path),
                },
            )
            message = EmailMessage(subject, html, to=[profile.user.email])
            message.content_subtype = "html"
            message.send(fail_silently=False)
    finally:
        clear_rls_context()
