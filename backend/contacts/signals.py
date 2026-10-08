"""Contact stage clock and durable record history."""

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from common.record_history import capture_changes, record, related_contact  # noqa: F401
from contacts.models import Contact


@receiver(pre_save, sender=Contact)
def before_contact(sender, instance, raw=False, update_fields=None, **kwargs):
    if raw:
        return
    old = capture_changes(sender, instance, update_fields)
    if old is None or (
        old.stage != instance.stage
        and (update_fields is None or "stage" in update_fields)
    ):
        instance.stage_entered_at = timezone.now() if instance.stage else None
        instance._stage_clock_changed = True
    else:
        instance._stage_clock_changed = False
        instance.stage_entered_at = old.stage_entered_at


@receiver(post_save, sender=Contact)
def after_contact(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    # update_fields may exclude the server-managed clock; persist it explicitly.
    if instance._stage_clock_changed:
        sender.objects.filter(pk=instance.pk).update(
            stage_entered_at=instance.stage_entered_at
        )
    if created:
        record(instance, "CREATE", "Contact created", actor=instance.created_by)
    elif instance._audit_changes:
        record(instance, "UPDATE", "Contact updated", instance._audit_changes)


@receiver(post_delete, sender=Contact)
def deleted_contact(sender, instance, origin=None, **kwargs):
    if (
        origin is not None
        and not isinstance(origin, Contact)
        and getattr(origin, "model", None) is not Contact
    ):
        return
    record(instance, "DELETE", "Contact deleted")
