"""Company activity using the same change tracking as Contacts."""

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from accounts.models import Account
from common.record_history import capture_changes, record


@receiver(pre_save, sender=Account)
def before_company(sender, instance, raw=False, update_fields=None, **kwargs):
    if not raw:
        capture_changes(sender, instance, update_fields)


@receiver(post_save, sender=Account)
def after_company(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    if created:
        record(instance, "CREATE", "Company created", actor=instance.created_by)
    elif instance._audit_changes:
        record(instance, "UPDATE", "Company updated", instance._audit_changes)


@receiver(post_delete, sender=Account)
def deleted_company(sender, instance, origin=None, **kwargs):
    if (
        origin is not None
        and not isinstance(origin, Account)
        and getattr(origin, "model", None) is not Account
    ):
        return
    record(instance, "DELETE", "Company deleted")
