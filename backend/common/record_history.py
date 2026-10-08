"""Shared meaningful activity for Contacts and Companies; reads never create events."""

import json

from crum import get_current_request
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver

from accounts.models import Account
from common.models import Activity, Attachments, Comment, Profile
from contacts.models import Contact


def record(contact, action, description, changes=None, actor=None, resource=None):
    if action in {"VIEW", "OPEN", "DOWNLOAD"}:
        return
    if action in {"UPDATE", "ASSIGN", "COMMENT"} and not changes:
        return
    request = get_current_request()
    profile = getattr(request, "profile", None)
    if profile is not None and profile.org_id != contact.org_id:
        profile = None
    if profile is None and actor:
        profile = Profile.objects.filter(
            org_id=contact.org_id, user_id=actor.pk
        ).first()
    Activity.objects.create(
        org_id=contact.org_id,
        user=profile,
        entity_type=contact.__class__.__name__,
        entity_id=contact.pk,
        entity_name=contact.name[:255],
        action=action,
        description=description,
        metadata=json.loads(
            json.dumps(
                {
                    "actor": profile.user.display_name
                    if profile
                    else "System / actor unavailable",
                    "changes": changes or {},
                    "resource": resource,
                },
                cls=DjangoJSONEncoder,
            )
        ),
    )


def capture_changes(sender, instance, update_fields=None):
    old = (
        sender.objects.filter(pk=instance.pk).first()
        if not instance._state.adding
        else None
    )
    instance._audit_changes = {}
    for field in instance._meta.concrete_fields:
        if field.name in {
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "stage_entered_at",
            "phone_match_key",
            "merged_into",
            "merged_at",
            "merge_snapshot",
        }:
            continue
        if (
            update_fields is not None
            and field.name not in update_fields
            and field.attname not in update_fields
        ):
            continue
        before = getattr(old, field.attname) if old else None
        after = getattr(instance, field.attname)
        if old and before != after:
            instance._audit_changes[field.name] = {
                "before": before,
                "after": after,
                "label": str(field.verbose_name or field.name).capitalize(),
            }
            if field.choices:
                choices = dict(field.flatchoices)
                instance._audit_changes[field.name]["before_display"] = choices.get(
                    before, before
                )
                instance._audit_changes[field.name]["after_display"] = choices.get(
                    after, after
                )

    return old


def related_contact(instance):
    model = instance.content_type.model_class()
    if model in (Contact, Account):
        return model.objects.filter(
            pk=instance.object_id, org_id=instance.org_id
        ).first()
    return None


@receiver(pre_save, sender=Comment)
@receiver(pre_save, sender=Attachments)
def before_note(sender, instance, raw=False, **kwargs):
    if not raw:
        instance._previous_note = (
            sender.objects.filter(pk=instance.pk)
            .values_list("comment" if sender is Comment else "file_name", flat=True)
            .first()
        )


@receiver(post_save, sender=Comment)
@receiver(post_save, sender=Attachments)
def related_saved(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    contact = related_contact(instance)
    if contact:
        kind = "Note" if sender is Comment else "Attachment"
        changes = {}
        if sender is Comment:
            changes["Note"] = {
                "before": getattr(instance, "_previous_note", None),
                "after": instance.comment,
            }
        else:
            changes["File"] = {
                "before": getattr(instance, "_previous_note", None),
                "after": instance.file_name,
            }
        if all(change["before"] == change["after"] for change in changes.values()):
            return
        record(
            contact,
            "COMMENT" if sender is Comment else "UPDATE",
            f"{kind} {'added' if created else 'updated'}",
            changes,
            resource={"type": kind, "id": str(instance.pk)},
        )


@receiver(post_delete, sender=Comment)
@receiver(post_delete, sender=Attachments)
def related_deleted(sender, instance, origin=None, **kwargs):
    if (
        origin is not None
        and not isinstance(origin, sender)
        and getattr(origin, "model", None) is not sender
    ):
        return
    contact = related_contact(instance)
    if contact:
        kind = "Note" if sender is Comment else "Attachment"
        value = instance.comment if sender is Comment else instance.file_name
        record(
            contact,
            "UPDATE",
            f"{kind} deleted",
            {kind: {"before": value, "after": None}},
            resource={"type": kind, "id": str(instance.pk)},
        )


def members(model, ids):
    rows = model.objects.filter(pk__in=ids).order_by("pk")
    if model is Profile:
        rows = rows.select_related("user")
    return [
        {
            "id": str(row.pk),
            "name": row.user.display_name
            if model is Profile
            else str(getattr(row, "name", None) or row),
        }
        for row in rows
    ]


def record_links(model, sender, instance, action, pk_set):
    fields = [f for f in sender._meta.fields if f.is_relation]
    contact_field = next((f for f in fields if f.related_model is model), None)
    if not contact_field or len(fields) != 2:
        return
    other = next(f for f in fields if f is not contact_field)
    key = f"_record_audit_{model.__name__}_{sender._meta.db_table}"
    if action.startswith("pre_"):
        if isinstance(instance, model):
            ids = [instance.pk]
        elif pk_set is not None:
            ids = pk_set
        else:
            ids = sender.objects.filter(**{other.attname: instance.pk}).values_list(
                contact_field.attname, flat=True
            )
        snapshot = {}
        for contact in model.objects.filter(pk__in=ids, org_id=instance.org_id):
            related_ids = sender.objects.filter(
                **{contact_field.attname: contact.pk}
            ).values_list(other.attname, flat=True)
            snapshot[contact.pk] = (contact, members(other.related_model, related_ids))
        setattr(instance, key, snapshot)
    elif action.startswith("post_"):
        for contact, before in getattr(instance, key, {}).values():
            related_ids = sender.objects.filter(
                **{contact_field.attname: contact.pk}
            ).values_list(other.attname, flat=True)
            after = members(other.related_model, related_ids)
            if before != after:
                label = (
                    "Owner"
                    if other.related_model is Profile
                    else str(other.related_model._meta.verbose_name_plural)
                )
                record(
                    contact,
                    "ASSIGN" if other.related_model is Profile else "UPDATE",
                    f"Changed {label}",
                    {label: {"before": before, "after": after}},
                )


@receiver(m2m_changed)
def audit_record_links(sender, instance, action, pk_set, **kwargs):
    for model in (Contact, Account):
        record_links(model, sender, instance, action, pk_set)


def history_for(instance):
    rows = (
        Activity.objects.filter(
            org_id=instance.org_id,
            entity_type=instance.__class__.__name__,
            entity_id=instance.pk,
        )
        .exclude(action__in=["VIEW", "OPEN", "DOWNLOAD"])
        .select_related("user__user")
        .order_by("-created_at", "-id")
    )
    return [
        {
            "id": str(row.pk),
            "action": row.action,
            "description": row.description or row.get_action_display(),
            "created_at": row.created_at,
            "actor": (
                row.user.user.display_name
                if row.user
                else row.metadata.get("actor") or "System / actor unavailable"
            ),
            "resource": row.metadata.get("resource"),
            "changes": row.metadata.get("changes", {}),
        }
        for row in rows
    ]
