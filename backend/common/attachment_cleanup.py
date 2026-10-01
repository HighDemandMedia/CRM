"""Durable, idempotent removal of storage objects after database deletion."""

import logging

from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import F
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone

from common.models import Attachments, PendingFileDeletion

logger = logging.getLogger(__name__)


def enqueue_cleanup():
    from common.tasks import purge_deleted_attachment_files

    try:
        purge_deleted_attachment_files.delay()
    except Exception:
        # Beat retries the durable rows even if the broker is unavailable.
        logger.exception("Attachment cleanup dispatch failed; scheduled retry retained")


@receiver(post_delete, sender=Attachments)
def remember_deleted_file(sender, instance, using, **kwargs):
    if instance.attachment:
        PendingFileDeletion.objects.using(using).create(name=instance.attachment.name)
        transaction.on_commit(enqueue_cleanup, using=using)


def purge_files():
    # Only storage keys are retained in this internal queue. Keeping it
    # independent of Org lets cleanup survive deletion of a tenant.
    jobs = PendingFileDeletion.objects.order_by(
        F("last_attempt_at").asc(nulls_first=True), "created_at"
    )[:100]
    for job in jobs:
        PendingFileDeletion.objects.filter(pk=job.pk).update(
            last_attempt_at=timezone.now(), attempts=F("attempts") + 1
        )
        try:
            default_storage.delete(job.name)
        except Exception:
            logger.exception("Attachment storage cleanup failed for job %s", job.pk)
        else:
            PendingFileDeletion.objects.filter(pk=job.pk).delete()
