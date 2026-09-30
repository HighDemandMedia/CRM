"""Recipients are active members who can view the resulting CRM record."""

from common.models import Profile
from common.notifications import create
from common.rbac import permitted


def recipients(submission):
    form = submission.form
    record = submission.contact or submission.lead
    if record is None:
        return []
    ids = set(form.notify_profiles.values_list("pk", flat=True))
    if form.assign_to_id:
        ids.add(form.assign_to_id)
    # A returning contact keeps its owner, who also needs to know about the enquiry.
    ids.update(record.assigned_to.values_list("pk", flat=True))
    profiles = Profile.objects.filter(
        pk__in=ids,
        org_id=form.org_id,
        is_active=True,
        removed_at__isnull=True,
        user__is_active=True,
    ).select_related("user")
    return [profile for profile in profiles if permitted(profile, record)]


def record_link(submission):
    return (
        f"/contacts/{submission.contact_id}"
        if submission.contact_id
        else f"/leads/{submission.lead_id}"
    )


def notify_in_app(submission):
    if not submission.form.notify_in_app:
        return
    for profile in recipients(submission):
        create(
            profile,
            "webform.submitted",
            entity=submission.contact or submission.lead,
            entity_name=submission.form.name,
            link=record_link(submission),
            data={"submission_id": str(submission.pk)},
        )
