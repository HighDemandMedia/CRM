"""Durable, idempotent removal of storage objects after database deletion."""

import logging

from django.core.files.storage import default_storage
from django.db import connection, transaction
from django.db.models import F
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone

from common.models import (
    Attachments,
    CommentFiles,
    Document,
    Org,
    PendingFileDeletion,
    User,
)
from invoices.models import InvoiceTemplate

logger = logging.getLogger(__name__)


def enqueue_cleanup():
    from common.tasks import purge_deleted_attachment_files

    try:
        purge_deleted_attachment_files.delay()
    except Exception:
        # Beat retries the durable rows even if the broker is unavailable.
        logger.exception("Attachment cleanup dispatch failed; scheduled retry retained")


FILE_FIELDS = {
    Attachments: "attachment",
    CommentFiles: "comment_file",
    Document: "document_file",
    Org: "logo",
    InvoiceTemplate: "logo",
}


@receiver(post_delete, sender=Attachments)
@receiver(post_delete, sender=CommentFiles)
@receiver(post_delete, sender=Document)
@receiver(post_delete, sender=Org)
@receiver(post_delete, sender=InvoiceTemplate)
def remember_deleted_file(sender, instance, using, **kwargs):
    file = getattr(instance, FILE_FIELDS[sender])
    if file:
        PendingFileDeletion.objects.using(using).get_or_create(
            name=file.name,
            org_id=instance.pk if sender is Org else instance.org_id,
        )
        transaction.on_commit(enqueue_cleanup, using=using)


def referenced_file_names(names):
    """Conservatively retain a key still referenced by any tenant or shared user.

    RLS means a single unscoped query cannot check other tenants. This internal
    worker visits each context and restores the caller's context afterwards.
    """
    from common.tasks import set_rls_context

    referenced = set(Org.objects.filter(logo__in=names).values_list("logo", flat=True))
    referenced.update(
        User.objects.filter(profile_image__in=names).values_list(
            "profile_image", flat=True
        )
    )
    previous = None
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.current_org', true)")
            previous = cursor.fetchone()[0]
    try:
        for org_id in Org.objects.values_list("pk", flat=True).iterator():
            set_rls_context(org_id)
            for model, field in FILE_FIELDS.items():
                if model is not Org:
                    referenced.update(
                        model.objects.filter(
                            org_id=org_id, **{f"{field}__in": names}
                        ).values_list(field, flat=True)
                    )
    finally:
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('app.current_org', %s, false)", [previous or ""]
                )
    return referenced


def purge_files():
    # Only storage keys are retained in this internal queue. Keeping it
    # independent of Org lets cleanup survive deletion of a tenant.
    jobs = list(
        PendingFileDeletion.objects.order_by(
            F("last_attempt_at").asc(nulls_first=True), "created_at"
        )[:100]
    )
    referenced = referenced_file_names([job.name for job in jobs]) if jobs else set()
    for job in jobs:
        PendingFileDeletion.objects.filter(pk=job.pk).update(
            last_attempt_at=timezone.now(), attempts=F("attempts") + 1
        )
        if job.name in referenced:
            # Another record owns this key. Its later deletion creates its own job.
            PendingFileDeletion.objects.filter(pk=job.pk).delete()
            continue
        try:
            default_storage.delete(job.name)
        except Exception:
            logger.exception("Attachment storage cleanup failed for job %s", job.pk)
        else:
            PendingFileDeletion.objects.filter(pk=job.pk).delete()

    from common.organization_purge import finish_file_deletions

    finish_file_deletions()
