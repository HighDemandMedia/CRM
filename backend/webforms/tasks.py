"""Deliver accepted web form submissions without blocking website visitors."""

import logging
from datetime import timedelta
from uuid import uuid4

from celery import shared_task
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from common.models import Org
from common.notification_preferences import channels_for
from common.organization_lifecycle import organization_job
from common.tasks import clear_rls_context, send_email, set_rls_context
from webforms.email_content import confirmation_email, internal_email
from webforms.models import WebFormSubmission
from webforms.notifications import recipients

logger = logging.getLogger(__name__)


@shared_task
@organization_job
def send_webform_submission_email(submission_id, org_id):
    set_rls_context(org_id)
    try:
        if Org.objects.filter(pk=org_id, is_active=True).exists():
            error = None
            # One failed internal recipient must not prevent acknowledging the
            # visitor. Each delivery has its own claim and completion state.
            for deliver in (_deliver, _deliver_confirmation):
                try:
                    deliver(submission_id, org_id)
                except Exception as exc:
                    logger.warning(
                        "Web form email delivery failed: %s (%s)",
                        submission_id,
                        type(exc).__name__,
                    )
                    error = error or exc
            if error is not None:
                raise error
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
                    if p.user.email
                    and str(p.pk) not in submission.email_delivered_to
                    and channels_for(p, "webform.submitted")["email"]
                ]
                if form.notify_email
                else []
            )
            if not pending:
                submission.email_completed_at = timezone.now()
                submission.save(update_fields=["email_completed_at"])
                return
            profile = pending[0]
            message = internal_email(submission, profile)
            claim = uuid4()
            submission.email_claim_id = claim
            submission.email_claimed_at = timezone.now()
            submission.save(update_fields=["email_claim_id", "email_claimed_at"])
        try:
            send_email(
                **message,
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


def _deliver_confirmation(submission_id, org_id):
    with transaction.atomic():
        submission = (
            WebFormSubmission.objects.select_for_update()
            .filter(pk=submission_id, org_id=org_id)
            .first()
        )
        if (
            not submission
            or submission.status not in WebFormSubmission.ACCEPTED_STATUSES
            or not submission.confirmation_requested
            or submission.confirmation_completed_at
        ):
            return
        if (
            submission.confirmation_claimed_at
            and submission.confirmation_claimed_at
            > timezone.now() - timedelta(minutes=5)
        ):
            return
        # Never fall back to a record owner, a notification recipient or a
        # changed contact email. Only the accepted, validated submission email.
        recipient = submission.payload.get("email", "")
        recipient = recipient.strip() if isinstance(recipient, str) else ""
        try:
            validate_email(recipient)
        except ValidationError:
            recipient = ""
        if not submission.form.send_confirmation_email or not recipient:
            submission.confirmation_completed_at = timezone.now()
            submission.save(update_fields=["confirmation_completed_at"])
            return
        message = confirmation_email(submission)
        claim = uuid4()
        submission.confirmation_claim_id = claim
        submission.confirmation_claimed_at = timezone.now()
        submission.save(
            update_fields=["confirmation_claim_id", "confirmation_claimed_at"]
        )
    try:
        send_email(**message, recipients=[recipient])
    except Exception:
        WebFormSubmission.objects.filter(
            pk=submission_id, org_id=org_id, confirmation_claim_id=claim
        ).update(confirmation_claim_id=None, confirmation_claimed_at=None)
        raise
    WebFormSubmission.objects.filter(
        pk=submission_id, org_id=org_id, confirmation_claim_id=claim
    ).update(
        confirmation_completed_at=timezone.now(),
        confirmation_claim_id=None,
        confirmation_claimed_at=None,
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
        Org.objects.filter(is_active=True, closing_at__isnull=True)
        .values_list("pk", flat=True)
        .iterator()
    ):
        set_rls_context(org_id)
        try:
            ids = (
                WebFormSubmission.objects.filter(
                    Q(email_completed_at__isnull=True)
                    | Q(
                        confirmation_requested=True,
                        confirmation_completed_at__isnull=True,
                    ),
                    org_id=org_id,
                    status__in=WebFormSubmission.ACCEPTED_STATUSES,
                )
                .order_by("created_at")
                .values_list("pk", flat=True)[:100]
            )
            for pk in ids:
                queue_notification(pk, org_id)
        finally:
            clear_rls_context()
