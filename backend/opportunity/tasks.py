import logging
from collections import defaultdict

from celery import shared_task
from celery.contrib.django.task import DjangoTask
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import connection
from django.template.loader import render_to_string
from django.utils import timezone

from common.links import frontend_url
from common.models import Org, Profile
from common.organization_lifecycle import organization_job
from opportunity.models import Opportunity, StageAgingConfig

logger = logging.getLogger(__name__)


def _set_rls_context_safe(org_id):
    """Set RLS context, skipping on non-PostgreSQL backends."""
    if connection.vendor == "postgresql":
        from common.tasks import set_rls_context

        set_rls_context(org_id)


@shared_task(base=DjangoTask)
@organization_job
def send_email_to_assigned_user(recipients, opportunity_id, org_id):
    from common.assignment_emails import send_assignment_emails

    send_assignment_emails(
        Opportunity,
        opportunity_id,
        org_id,
        recipients,
        template="assigned_to/opportunity_assigned.html",
        context_key="opportunity",
        path=f"/pipeline/{opportunity_id}",
        subject="Deal assigned · HDM CRM",
    )


@shared_task
def check_stale_opportunities():
    """Daily task: find rotten deals across all orgs and send email alerts."""
    from opportunity.workflow import (
        CLOSED_STAGES,
        DEFAULT_STAGE_EXPECTED_DAYS,
        ROTTEN_MULTIPLIER,
    )

    now = timezone.now()
    orgs = Org.objects.filter(is_active=True, closing_at__isnull=True)

    for org in orgs:
        try:
            _set_rls_context_safe(str(org.id))

            aging_configs = {
                c.stage: c for c in StageAgingConfig.objects.filter(org=org)
            }

            open_opps = (
                Opportunity.objects.filter(org=org, is_active=True)
                .exclude(stage__in=CLOSED_STAGES)
                .select_related("org")
            )

            stale_opps = []
            for opp in open_opps:
                if not opp.stage_changed_at:
                    continue
                config = aging_configs.get(opp.stage)
                expected = (
                    config.expected_days
                    if config
                    else DEFAULT_STAGE_EXPECTED_DAYS.get(opp.stage)
                )
                if expected is None:
                    continue
                days = (now - opp.stage_changed_at).days
                if days >= expected * ROTTEN_MULTIPLIER:
                    stale_opps.append((opp, days, expected))

            if stale_opps:
                send_stale_deals_alert(org, stale_opps)
        except Exception:
            logger.exception("Error processing stale deals for org %s", org.id)


@organization_job
def send_stale_deals_alert(org, stale_opps):
    """Send per-user email alerts for rotten deals."""
    # Pre-fetch org admins for unassigned deals
    org_admins = list(Profile.objects.filter(org=org, role="ADMIN", is_active=True))

    # Group by assigned users
    user_deals = defaultdict(list)
    for opp, days, expected in stale_opps:
        assigned = list(opp.assigned_to.filter(is_active=True))
        if assigned:
            for profile in assigned:
                user_deals[profile].append((opp, days, expected))
        else:
            # No one assigned - alert org admins
            for admin in org_admins:
                user_deals[admin].append((opp, days, expected))

    for profile, deals in user_deals.items():
        context = {
            "user": profile.user,
            "deals": [
                {
                    "name": opp.name,
                    "stage": opp.get_stage_display(),
                    "days_in_stage": days,
                    "expected_days": expected,
                }
                for opp, days, expected in deals
            ],
            "url": frontend_url("/pipeline?rotten=true"),
            "deal_count": len(deals),
        }
        subject = f"{len(deals)} deal{'s' if len(deals) > 1 else ''} need{'s' if len(deals) == 1 else ''} attention · HDM CRM"
        html_content = render_to_string(
            "opportunity/stale_deals_alert.html", context=context
        )
        msg = EmailMessage(
            subject,
            html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[profile.user.email],
        )
        msg.content_subtype = "html"
        try:
            msg.send()
        except Exception:
            logger.exception(
                "Failed to send stale deals alert to %s", profile.user.email
            )
