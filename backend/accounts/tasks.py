import logging

from celery import shared_task
from celery.contrib.django.task import DjangoTask
from django.core.mail import EmailMessage
from django.template import Context, Template

from accounts.models import Account, AccountEmail, AccountEmailLog
from common.organization_lifecycle import organization_job
from common.tasks import set_rls_context

logger = logging.getLogger(__name__)


@shared_task
@organization_job
def send_email(email_obj_id, org_id):
    set_rls_context(org_id)
    try:
        email_obj = AccountEmail.objects.get(id=email_obj_id)
    except AccountEmail.DoesNotExist:
        logger.error("AccountEmail id=%s not found, skipping task.", email_obj_id)
        return
    else:
        from_email = email_obj.from_email
        contacts = email_obj.recipients.all()
        for contact_obj in contacts:
            if not AccountEmailLog.objects.filter(
                email=email_obj, contact=contact_obj, is_sent=True
            ).exists():
                html = email_obj.message_body
                context_data = {
                    "email": contact_obj.email if contact_obj.email else "",
                    "name": (
                        contact_obj.first_name
                        if contact_obj.first_name
                        else (
                            "" + " " + contact_obj.last_name
                            if contact_obj.last_name
                            else ""
                        )
                    ),
                }
                try:
                    html_content = Template(html).render(Context(context_data))
                    subject = email_obj.message_subject
                    msg = EmailMessage(
                        subject,
                        html_content,
                        from_email=from_email,
                        to=[
                            contact_obj.email,
                        ],
                    )
                    msg.content_subtype = "html"
                    res = msg.send()
                    if res:
                        email_obj.rendered_message_body = html_content
                        email_obj.save()
                        AccountEmailLog.objects.create(
                            email=email_obj, contact=contact_obj, is_sent=True
                        )
                except Exception:
                    pass


@shared_task(base=DjangoTask)
@organization_job
def send_email_to_assigned_user(recipients, account_id, org_id):
    from common.assignment_emails import send_assignment_emails

    send_assignment_emails(
        Account,
        account_id,
        org_id,
        recipients,
        template="assigned_to/account_assigned.html",
        context_key="account",
        path=f"/accounts/{account_id}",
        subject="Company assigned · HDM CRM",
    )
