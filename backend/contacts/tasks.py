from celery import shared_task
from celery.contrib.django.task import DjangoTask

from common.organization_lifecycle import organization_job
from contacts.models import Contact


@shared_task(base=DjangoTask)
@organization_job
def send_email_to_assigned_user(recipients, contact_id, org_id):
    from common.assignment_emails import send_assignment_emails

    send_assignment_emails(
        Contact,
        contact_id,
        org_id,
        recipients,
        template="assigned_to/contact_assigned.html",
        context_key="contact",
        path=f"/contacts/{contact_id}",
        subject="Contact assigned · HDM CRM",
    )
