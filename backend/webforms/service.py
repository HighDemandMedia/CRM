"""The single lead write path for web form submissions.

Both `webforms.public_views.WebFormSubmitView` and the legacy
`leads.views.lead_interactions.CreateLeadFromSite` go through here. That is the
point: the legacy endpoint had six separate defects in its own copy of this
logic, and one shared implementation is what stops them being fixed once and
reintroduced next to it.

Everything this module writes to a Lead is derived from the form row or from
values a serializer has already validated. Nothing is read from a request.
"""

import logging

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.db.models.functions import Lower

from common.models import Comment
from contacts.models import Contact
from leads.models import Lead
from webforms.constants import CONTACT_FIELD_VALUES
from webforms.models import WebForm, WebFormSubmission

logger = logging.getLogger(__name__)

# The Lead columns the merge path may fill in on a repeat submission.
# Assignment, status, source and the pipeline columns are absent on purpose:
# those belong to whoever owns the lead now, not to a stranger who happens to
# know their email address.
MERGEABLE_FIELDS = [
    "salutation",
    "first_name",
    "last_name",
    "phone",
    "company_name",
    "job_title",
    "website",
    "title",
    "city",
    "state",
    "country",
    "postcode",
    "industry",
]


def _existing_lead(form, email):
    """The org's lead with this address, if there is one.

    Case-insensitive, because `Lead` enforces uniqueness on `Lower("email")`.
    Matching case-sensitively here would find nothing and then hit the
    constraint on insert, which is exactly the 500 this function exists to
    avoid.

    Scoped to the form's org. A lead in another tenant with the same address is
    a different person, and merging across that boundary would leak one org's
    record into another's form.
    """
    if not email:
        return None
    return (
        Lead.objects.filter(org=form.org)
        .annotate(email_lower=Lower("email"))
        .filter(email_lower=email.lower())
        .first()
    )


def _owner(form):
    """The Profile credited with the submission's comment, or None.

    A web form submission has no request user, so this is the form's configured
    assignee. There is deliberately no fallback to `form.created_by`: that is a
    User and `Comment.commented_by` is a Profile, so the two are not
    interchangeable. `commented_by` is nullable, and a comment with no author
    is the honest record of a form nobody is assigned to.
    """
    return form.assign_to


def _created_by_user(form):
    """The User stamped on `Lead.created_by`.

    `Lead.created_by` points at a User while `assign_to` is a Profile, so this
    reaches through. Falls back to the form's own creator when the form has no
    assignee, because a lead with no creator is one nobody can be asked about.
    """
    assignee = form.assign_to
    if assignee is not None and assignee.user_id:
        return assignee.user
    return form.created_by


def _create_lead(form, values, custom_fields):
    lead = Lead(
        org=form.org,
        # Server-derived, never from the submission.
        status="assigned",
        source=form.lead_source,
        is_active=True,
        created_by=_created_by_user(form),
        custom_fields=dict(custom_fields or {}),
    )
    for key, value in values.items():
        setattr(lead, key, value)
    lead.save()

    if form.assign_to is not None:
        lead.assigned_to.add(form.assign_to)
    tags = list(form.tags.all())
    if tags:
        lead.tags.add(*tags)
    return lead


def _merge_lead(form, lead, values, custom_fields):
    """Fill blanks only, then record the new message as a comment.

    Overwriting a populated field is deliberately excluded. Anyone who knows a
    prospect's email address can post this form, so allowing an overwrite would
    let a stranger rewrite that prospect's record.
    """
    changed = []
    for key in MERGEABLE_FIELDS:
        incoming = values.get(key)
        if not incoming:
            continue
        if getattr(lead, key, None):
            continue
        setattr(lead, key, incoming)
        changed.append(key)

    custom_changed = False
    for key, value in (custom_fields or {}).items():
        if lead.custom_fields.get(key) in (None, "", []):
            lead.custom_fields[key] = value
            custom_changed = True
    if custom_changed:
        changed.append("custom_fields")

    if changed:
        lead.save(update_fields=sorted(set(changed)) + ["updated_at"])

    message = values.get("description") or ""
    if message:
        Comment.objects.create(
            org=form.org,
            content_type=ContentType.objects.get_for_model(Lead),
            object_id=lead.id,
            comment=f"Web form submission ({form.name}):\n{message}",
            commented_by=_owner(form),
        )
    return lead


@transaction.atomic
def submit_form(
    form,
    values,
    *,
    custom_fields=None,
    ip=None,
    referer="",
    rejected=None,
    reason="",
    request_id=None,
):
    """Record one submission and create or merge its lead.

    `values` is the VALIDATED dict keyed by Lead attribute name, never raw
    request data. `custom_fields` is a separate map keyed by
    CustomFieldDefinition key, because those land in a JSON column rather than
    on a Lead attribute.

    `rejected`, when set to a WebFormSubmission rejection status, records the
    attempt and writes no lead at all.

    Returns the WebFormSubmission. Callers read `.status` to decide what to
    tell the visitor, and must never leak `.reject_reason`, which is triage
    detail: telling a bot which control caught it is how it learns to get past
    that control.
    """
    if rejected is not None:
        return WebFormSubmission.objects.create(
            org=form.org,
            form=form,
            lead=None,
            payload=values or {},
            status=rejected,
            reject_reason=reason[:255],
            submitted_ip=ip,
            referer=referer,
        )

    # Serialize retries for this form. The Contact unique-email constraint
    # also resolves concurrent submissions through two different forms.
    WebForm.objects.select_for_update().get(pk=form.pk, org_id=form.org_id)
    if request_id:
        previous = WebFormSubmission.objects.filter(
            form=form, org=form.org, request_id=request_id
        ).first()
        if previous:
            return previous
    if form.target_model == "Contact":
        return _submit_contact(form, values, custom_fields, ip, referer, request_id)
    email = values.get("email")
    existing = _existing_lead(form, email)
    if existing is not None:
        lead = _merge_lead(form, existing, values, custom_fields)
        status = WebFormSubmission.ACCEPTED_DUPLICATE
    else:
        lead = _create_lead(form, values, custom_fields)
        status = WebFormSubmission.ACCEPTED

    payload = dict(values)
    if custom_fields:
        payload["custom_fields"] = dict(custom_fields)

    submission = WebFormSubmission.objects.create(
        org=form.org,
        form=form,
        lead=lead,
        request_id=request_id,
        payload=payload,
        status=status,
        submitted_ip=ip,
        referer=referer,
    )
    from webforms.notifications import notify_in_app

    notify_in_app(submission)
    return submission


def _submit_contact(form, values, custom_fields, ip, referer, request_id):
    email = values["email"].strip().lower()
    existing = Contact.objects.filter(org_id=form.org_id, email__iexact=email).first()
    contact = existing
    if contact is None:
        safe_values = {
            key: value for key, value in values.items() if key in CONTACT_FIELD_VALUES
        }
        safe_values["email"] = email
        try:
            # Savepoint lets a simultaneous website/CRM creation win safely.
            with transaction.atomic():
                contact = Contact.objects.create(
                    org=form.org,
                    stage="LEAD",
                    source=form.contact_source,
                    created_by=_created_by_user(form),
                    auto_created=True,
                    custom_fields=custom_fields or {},
                    **safe_values,
                )
        except IntegrityError:
            contact = Contact.objects.filter(
                org_id=form.org_id, email__iexact=email
            ).first()
            if contact is None:
                raise
            existing = contact
        if existing is None:
            if (
                form.assign_to
                and form.assign_to.org_id == form.org_id
                and form.assign_to.is_active
            ):
                contact.assigned_to.add(form.assign_to)
            contact.tags.add(*form.tags.filter(org_id=form.org_id))
    # Public senders may append a message, but cannot rewrite a known contact.
    message = values.get("description")
    if message:
        Comment.objects.create(
            org=form.org,
            content_type=ContentType.objects.get_for_model(Contact),
            object_id=contact.pk,
            commented_by=None,
            comment=f"Website form: {form.name}\n{message}",
        )
    payload = dict(values)
    if custom_fields:
        payload["custom_fields"] = custom_fields
    submission = WebFormSubmission.objects.create(
        org=form.org,
        form=form,
        contact=contact,
        request_id=request_id,
        payload=payload,
        submitted_ip=ip,
        referer=referer,
        status=WebFormSubmission.ACCEPTED_DUPLICATE
        if existing
        else WebFormSubmission.ACCEPTED,
    )
    from webforms.notifications import notify_in_app

    notify_in_app(submission)
    return submission
