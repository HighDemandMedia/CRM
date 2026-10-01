"""Deliver accepted web form submissions without blocking website visitors."""

import logging
from datetime import timedelta
from uuid import uuid4

from celery import shared_task
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from common.links import frontend_url
from common.models import Org
from common.tasks import clear_rls_context, send_email, set_rls_context
from webforms.models import WebFormSubmission
from webforms.notifications import recipients, record_link

logger = logging.getLogger(__name__)


@shared_task
def send_webform_submission_email(submission_id, org_id):
    set_rls_context(org_id)
    try:
        if Org.objects.filter(pk=org_id, is_active=True).exists():
            _deliver(submission_id, org_id)
    finally:
        clear_rls_context()


def _deliver(submission_id, org_id):
    # Claim a recipient briefly; delivery must not hold a database lock.
    # As with any mail transport, a crash after acceptance but before the DB
    # acknowledgement can still result in a repeated email.
    while True:
        with transaction.atomic():
            submission = (
                WebFormSubmission.objects.select_for_update()
                .filter(
                    pk=submission_id,
                    org_id=org_id,
                )
                .first()
            )
            if (
                not submission
                or submission.status not in WebFormSubmission.ACCEPTED_STATUSES
                or submission.email_completed_at
            ):
                return
            if (
                submission.email_claimed_at
                and submission.email_claimed_at > timezone.now() - timedelta(minutes=5)
            ):
                return
            form = submission.form
            pending = (
                [
                    p
                    for p in recipients(submission)
                    if p.user.email and str(p.pk) not in submission.email_delivered_to
                ]
                if form.notify_email
                else []
            )
            if not pending:
                submission.email_completed_at = timezone.now()
                submission.save(update_fields=["email_completed_at"])
                return
            profile = pending[0]
            html = render_to_string(
                "webforms/submission_email.html",
                {
                    "form": form,
                    "submission": submission,
                    "record": submission.contact or submission.lead,
                    "record_url": frontend_url(record_link(submission)),
                    "is_duplicate": submission.status
                    == WebFormSubmission.ACCEPTED_DUPLICATE,
                },
            )
            claim = uuid4()
            submission.email_claim_id = claim
            submission.email_claimed_at = timezone.now()
            submission.save(update_fields=["email_claim_id", "email_claimed_at"])
        try:
            send_email(
                subject=f"New submission: {form.name}",
                html_content=html,
                recipients=[profile.user.email],
            )
        except Exception:
            WebFormSubmission.objects.filter(
                pk=submission_id, org_id=org_id, email_claim_id=claim
            ).update(email_claim_id=None, email_claimed_at=None)
            raise
        with transaction.atomic():
            current = (
                WebFormSubmission.objects.select_for_update()
                .filter(pk=submission_id, org_id=org_id, email_claim_id=claim)
                .first()
            )
            if not current:
                return
            current.email_delivered_to.append(str(profile.pk))
            current.email_claim_id = None
            current.email_claimed_at = None
            current.save(
                update_fields=[
                    "email_delivered_to",
                    "email_claim_id",
                    "email_claimed_at",
                ]
            )


def queue_notification(submission_id, org_id):
    try:
        send_webform_submission_email.delay(str(submission_id), str(org_id))
    except Exception:
        # The accepted submission is the outbox. Beat will enqueue it again.
        logger.exception("Web form email queued for later retry: %s", submission_id)


@shared_task
def retry_pending_webform_emails():
    for org_id in (
        Org.objects.filter(is_active=True).values_list("pk", flat=True).iterator()
    ):
        set_rls_context(org_id)
        try:
            ids = (
                WebFormSubmission.objects.filter(
                    org_id=org_id,
                    email_completed_at__isnull=True,
                    status__in=WebFormSubmission.ACCEPTED_STATUSES,
                )
                .order_by("created_at")
                .values_list("pk", flat=True)[:100]
            )
            for pk in ids:
                queue_notification(pk, org_id)
        finally:
            clear_rls_context()
