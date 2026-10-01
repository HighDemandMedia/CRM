import hashlib
import logging
from datetime import timedelta

from celery import shared_task
from django.core.mail import EmailMessage
from django.core.signing import TimestampSigner
from django.template.loader import render_to_string
from django.utils import timezone

from cases.models import Case, CsatSurvey
from cases.notifications import case_link
from common.links import frontend_url
from common.models import Profile
from common.tasks import set_rls_context

logger = logging.getLogger(__name__)

# Surveys live for 30 days from send before the link 410s.
CSAT_TOKEN_TTL_DAYS = 30
# Wait this long after a case closes before sending the survey, to avoid
# spamming customers when an agent flips status to Closed and then
# immediately reopens (Tier 1 reopen).
CSAT_SEND_DELAY_MINUTES = 30
# Salt scoping the TimestampSigner so a leak doesn't help forge tokens
# elsewhere in the codebase.
CSAT_SIGNER_SALT = "cases.csat_survey"
# The rating scale, in one place because two things read it: the survey email
# renders a star per value, and csat_views.CsatPublicView validates the POST
# against the same bounds. A scale that disagreed with the validator would put
# a star in the email that the API rejects on arrival.
CSAT_RATING_MIN = 1
CSAT_RATING_MAX = 5
# The ends of the scale, labelled. Mirrors SCALE_ENDS in the survey page so the
# email and the page it links to describe the same 1 and the same 5.
CSAT_SCALE_LOW_LABEL = "Not good"
CSAT_SCALE_HIGH_LABEL = "Great"


@shared_task
def send_email_to_assigned_user(recipients, case_id, org_id):
    """Send Mail To Users When they are assigned to a case"""
    set_rls_context(org_id)
    case = Case.objects.get(id=case_id)
    created_by = case.created_by
    for profile_id in recipients:
        recipients_list = []
        profile = Profile.objects.filter(id=profile_id, is_active=True).first()
        if profile:
            recipients_list.append(profile.user.email)
            context = {}
            context["url"] = frontend_url(case_link(case.id))
            context["user"] = profile.user
            context["case"] = case
            context["created_by"] = created_by
            subject = "Assigned to case."
            html_content = render_to_string(
                "assigned_to/cases_assigned.html", context=context
            )

            msg = EmailMessage(subject, html_content, to=recipients_list)
            msg.content_subtype = "html"
            msg.send()


# ---------------------------------------------------------------------------
# CSAT (Tier 2 csat)


def csat_signer() -> TimestampSigner:
    """Salted TimestampSigner shared by send + verify paths."""
    return TimestampSigner(salt=CSAT_SIGNER_SALT)


def hash_csat_token(token: str) -> str:
    """SHA-256 hex digest. We never store raw tokens, only their hash."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _select_primary_contact(case: Case):
    """Pick the contact we'll mail. Prefer one with a non-blank email.

    Cases with multiple contacts get a single survey to the first
    email-bearing one (FK iteration order). Spec: each closed case is one
    survey; do not bundle, do not split.
    """
    return (
        case.contacts.exclude(email__isnull=True)
        .exclude(email="")
        .order_by("created_at")
        .first()
    )


@shared_task
def send_csat_survey(case_id, org_id):
    """Send a CSAT survey for a freshly-closed case.

    Skips when:
      - The org has flipped `csat_enabled` off.
      - The case has no contact with an email (logged, not raised).
      - The case has been reopened in the meantime (status no longer
        Closed): the spec's reopen-protection clause.
      - A survey row already exists for this case (don't double-send).
    """
    set_rls_context(org_id)
    case = Case.objects.filter(id=case_id, org_id=org_id).first()
    if case is None:
        logger.info("send_csat_survey: case=%s not found, skipping", case_id)
        return None
    if case.status != "Closed":
        logger.info(
            "send_csat_survey: case=%s status=%s, likely reopened, skipping",
            case_id,
            case.status,
        )
        return None
    if not case.org.csat_enabled:
        logger.info("send_csat_survey: org=%s has csat disabled, skipping", org_id)
        return None
    if hasattr(case, "csat_survey"):
        logger.info("send_csat_survey: case=%s already has a survey row", case_id)
        return None

    contact = _select_primary_contact(case)
    if contact is None or not contact.email:
        logger.info("send_csat_survey: case=%s has no contact email, skipping", case_id)
        return None

    now = timezone.now()
    raw_token = csat_signer().sign(str(case.id))
    survey = CsatSurvey.objects.create(
        org_id=org_id,
        case=case,
        contact=contact,
        token_hash=hash_csat_token(raw_token),
        sent_at=now,
        expires_at=now + timedelta(days=CSAT_TOKEN_TTL_DAYS),
    )

    # Register the unscoped token→org lookup so the anonymous survey view can
    # resolve the org under RLS. hash_csat_token is sha256, matching the key
    # portal_token_hash computes from the same URL token.
    from common.portal_tokens import register_portal_token_hash

    register_portal_token_hash(survey.token_hash, org_id, "csat", survey.id)

    link = frontend_url(f"/csat/{raw_token}")
    context = {
        "case": case,
        "contact": contact,
        "org": case.org,
        "link": link,
        # Each value becomes a star linking to `{link}?rating=<value>`, which
        # only pre-selects on the page. Nothing is recorded until that page
        # POSTs, because a link is a GET and mail scanners follow GETs.
        "rating_scale": range(CSAT_RATING_MIN, CSAT_RATING_MAX + 1),
        "scale_low_label": CSAT_SCALE_LOW_LABEL,
        "scale_high_label": CSAT_SCALE_HIGH_LABEL,
    }
    # Deliberately unguarded. This render used to sit under a bare
    # `except Exception` that fell back to a plain link, with a comment saying
    # the template existed in production. It never existed anywhere, so every
    # survey ever sent took the fallback and nobody found out. A template that
    # fails to render is now a task failure that Celery logs.
    html = render_to_string("csat/survey_email.html", context=context)

    msg = EmailMessage(
        subject=f"How did we do?, {case.name}",
        body=html,
        to=[contact.email],
    )
    msg.content_subtype = "html"
    try:
        msg.send(fail_silently=False)
    except Exception:
        # The survey row is already written; a retry strategy can pick it
        # up by token_hash. We don't tear down the row because the agent
        # CAN re-send manually if needed.
        logger.exception(
            "send_csat_survey: email send failed for case=%s contact=%s",
            case_id,
            contact.id,
        )
    return str(survey.id)


@shared_task
def notify_portal_contacts(case_id, org_id, kind, actor_contact_id=None):
    """Tell the customer that something happened on their case.

    `kind` is "reply" or "status". Unlike `_select_primary_contact`, which
    deliberately picks a single recipient for CSAT, this mails every contact on
    the case that has an address, because any of them may be the one waiting.

    `actor_contact_id` is excluded, so nobody is emailed about their own reply.

    The link points at a page that requires signing in and carries no token, so
    forwarding the email does not forward access. That is the difference between
    this and the invoice and estimate mails, where the token in the URL is the
    whole credential.
    """
    set_rls_context(org_id)
    case = Case.objects.filter(id=case_id, org_id=org_id).first()
    if case is None:
        logger.info("notify_portal_contacts: case=%s not found, skipping", case_id)
        return None

    recipients = (
        case.contacts.filter(is_active=True)
        .exclude(email__isnull=True)
        .exclude(email="")
    )
    if actor_contact_id:
        recipients = recipients.exclude(id=actor_contact_id)

    # The org rides in the query string because the recipient may have no
    # portal cookie on the device they read this on: a phone, a colleague's
    # machine, a browser they cleared. Without it the sign-in fallback has no
    # idea which tenant's portal to send them to and drops them on the internal
    # staff login, which a customer cannot use. It is an id that already
    # appears in the URL of every portal page, not a credential, and it grants
    # nothing on its own.
    link = frontend_url(f"/portal/cases/{case.id}?org={case.org_id}")
    org_name = case.org.name or ""
    sent = 0
    for contact in recipients:
        html = render_to_string(
            "portal/case_update_email.html",
            {
                "contact_name": contact.first_name or "",
                "case_name": case.name,
                "case_status": case.status,
                "kind": kind,
                "link": link,
                "org_name": org_name,
            },
        )
        subject = (
            f"Re: {case.name}"
            if kind == "reply"
            else f"{case.name} is now {case.status}"
        )
        msg = EmailMessage(subject, html, to=[contact.email])
        msg.content_subtype = "html"
        try:
            msg.send(fail_silently=False)
            sent += 1
        except Exception:
            # One bad address must not stop the rest of the thread being told.
            logger.exception(
                "notify_portal_contacts: send failed for case=%s contact=%s",
                case_id,
                contact.id,
            )
    return sent


# ---------------------------------------------------------------------------
# Tier 3 time-tracking: auto-stop forgotten timers.

# A running timer this old gets killed by the Celery beat. Hand-tuned: 12h
# covers an overnight forgotten timer without clobbering a mid-day session
# someone left running through lunch.
TIME_ENTRY_AUTO_STOP_HOURS = 12
