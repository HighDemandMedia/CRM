"""Reviewed record merges shared by Contacts and Companies."""

import hashlib
import json
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.core import signing
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import (
    Activity,
    Attachments,
    Comment,
    CustomFieldDefinition,
    PortalLoginToken,
    Profile,
)
from common.permissions import HasOrgContext, is_org_admin
from common.pipeline_settings import stages_for, validate_entry


def encoded(value):
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


def snapshot(record):
    values = {
        field.name: getattr(record, field.attname)
        for field in record._meta.concrete_fields
        if field.name != "merge_snapshot"
    }
    for field in record._meta.many_to_many:
        values[field.name] = sorted(
            str(pk) for pk in getattr(record, field.name).values_list("pk", flat=True)
        )
    return encoded(values)


def version(record):
    return hashlib.sha256(
        json.dumps(snapshot(record), sort_keys=True).encode()
    ).hexdigest()


def property_rows(primary, secondary, fields):
    model = type(primary)
    target = model.__name__
    rows = []
    if primary.name != secondary.name:
        rows.append(
            {
                "key": "name",
                "label": "Name",
                "primary": primary.name,
                "secondary": secondary.name,
                "default": "primary" if primary.name else "secondary",
            }
        )
    stage_labels = {s["key"]: s["label"] for s in stages_for(primary.org, target)}
    for key in fields:
        field = model._meta.get_field(key)
        a, b = getattr(primary, field.attname), getattr(secondary, field.attname)
        if a == b or (a in (None, "") and b in (None, "")):
            continue

        def display(obj, value):
            if key == "account":
                return obj.account.name if obj.account_id else ""
            if key == "stage":
                return stage_labels.get(value, value)
            if field.choices:
                return dict(field.flatchoices).get(value, value)
            return value

        rows.append(
            {
                "key": key,
                "label": "Company"
                if key == "account"
                else str(field.verbose_name).capitalize(),
                "is_datetime": key == "appointment_at",
                "primary": encoded(display(primary, a)),
                "secondary": encoded(display(secondary, b)),
                "default": "secondary" if a in (None, "") else "primary",
            }
        )
    definitions = {
        d.key: d.label
        for d in CustomFieldDefinition.objects.filter(
            org=primary.org, target_model=target
        )
    }
    for key in sorted(
        set(primary.custom_fields or {}) | set(secondary.custom_fields or {})
    ):
        a, b = (
            (primary.custom_fields or {}).get(key),
            (secondary.custom_fields or {}).get(key),
        )
        if a != b:
            rows.append(
                {
                    "key": "custom_fields." + key,
                    "label": definitions.get(key, key),
                    "primary": a,
                    "secondary": b,
                    "default": "secondary" if a in (None, "", []) else "primary",
                }
            )
    return rows


def move_links(primary, secondary):
    """Move membership without firing notifications or recreating related records."""
    model_class = type(primary)
    for relation in model_class._meta.get_fields():
        if not relation.many_to_many:
            continue
        field = relation.field if relation.auto_created else relation
        through = field.remote_field.through
        if not through._meta.auto_created:
            raise ValidationError(
                "This record has an unsupported association. Nothing was merged."
            )
        contact_key = (
            field.m2m_reverse_field_name()
            if relation.auto_created
            else field.m2m_field_name()
        )
        other_key = (
            field.m2m_field_name()
            if relation.auto_created
            else field.m2m_reverse_field_name()
        )
        links = through.objects.filter(**{contact_key + "_id": secondary.pk})
        for other_id in links.values_list(other_key + "_id", flat=True):
            through.objects.get_or_create(
                **{contact_key + "_id": primary.pk, other_key + "_id": other_id}
            )
        links.delete()
    # Keep portal authorship and old login identities tied to the archived person.
    for relation in model_class._meta.related_objects:
        if not relation.one_to_many or relation.related_model in (
            model_class,
            Comment,
            PortalLoginToken,
        ):
            continue
        model = relation.related_model
        if not any(f.name == "org" for f in model._meta.fields):
            raise ValidationError(
                "This record has an unsupported relationship. Nothing was merged."
            )
        model.objects.filter(
            org_id=primary.org_id, **{relation.field.attname: secondary.pk}
        ).update(**{relation.field.attname: primary.pk})
    if model_class.__name__ == "Contact":
        from accounts.models import Account

        for account_id in {primary.account_id, secondary.account_id} - {None}:
            Account.contacts.through.objects.get_or_create(
                account_id=account_id, contact_id=primary.pk
            )
    content_type = ContentType.objects.get_for_model(model_class)
    for model in (Comment, Attachments):
        model.objects.filter(
            org_id=primary.org_id, content_type=content_type, object_id=secondary.pk
        ).update(object_id=primary.pk)
    Activity.objects.filter(
        org_id=primary.org_id, entity_type=model_class.__name__, entity_id=secondary.pk
    ).update(entity_id=primary.pk)
    if secondary.description and secondary.description != primary.description:
        # Preserve the original note's text and author, and its original timestamps.
        note = Comment.objects.create(
            org_id=primary.org_id,
            content_type=content_type,
            object_id=primary.pk,
            comment=secondary.description,
            is_internal=True,
            commented_by=Profile.objects.filter(
                org_id=secondary.org_id, user_id=secondary.created_by_id
            ).first(),
        )
        Comment.objects.filter(pk=note.pk).update(
            created_at=secondary.created_at, commented_on=secondary.created_at
        )
    if model_class.__name__ == "Contact":
        PortalLoginToken.objects.filter(
            org_id=primary.org_id, contact_id=secondary.pk, is_used=False
        ).update(is_used=True, used_at=timezone.now())


class RecordMergeView(APIView):
    model = None
    fields = ()
    search_fields = ()
    search_order = "name"
    noun = "record"
    plural = "records"
    salt = ""

    def rows(self, primary, secondary):
        return property_rows(primary, secondary, self.fields)

    permission_classes = (IsAuthenticated, HasOrgContext)

    def allowed(self, request):
        if not is_org_admin(request.profile):
            raise PermissionDenied(f"Only organization admins can merge {self.plural}.")

    def get(self, request, pk):
        self.allowed(request)
        primary = get_object_or_404(self.model.objects, pk=pk, org=request.profile.org)
        other = request.query_params.get("secondary")
        if not other:
            query = request.query_params.get("q", "").strip()[:255]
            qs = self.model.objects.filter(org=primary.org).exclude(pk=pk)
            if len(query) < 2:
                return Response({"results": []})
            match = Q()
            for field in self.search_fields:
                match |= Q(**{field + "__icontains": query})
            qs = qs.filter(match)
            return Response(
                {
                    "results": [
                        {
                            "id": str(c.pk),
                            "name": c.name,
                            "email": c.email,
                            "phone": c.phone,
                        }
                        for c in qs.order_by(self.search_order, "id")[:15]
                    ]
                }
            )
        try:
            other = UUID(other)
        except ValueError:
            raise ValidationError("Invalid record ID.")
        secondary = get_object_or_404(self.model.objects, pk=other, org=primary.org)
        if primary.pk == secondary.pk:
            raise ValidationError("Choose a different record.")
        token = signing.dumps(
            {
                "primary": str(primary.pk),
                "secondary": str(secondary.pk),
                "org": str(primary.org_id),
                "versions": [version(primary), version(secondary)],
            },
            salt=self.salt,
        )
        return Response(
            {
                "primary": {"id": str(primary.pk), "name": primary.name},
                "secondary": {"id": str(secondary.pk), "name": secondary.name},
                "properties": self.rows(primary, secondary),
                "token": token,
            }
        )

    @transaction.atomic
    def post(self, request, pk):
        self.allowed(request)
        if request.data.get("confirm") is not True:
            raise ValidationError("Confirm the merge after reviewing both records.")
        try:
            plan = signing.loads(
                request.data.get("token", ""), salt=self.salt, max_age=1800
            )
        except (signing.BadSignature, TypeError):
            raise ValidationError("Refresh the comparison before merging.")
        if plan["primary"] != str(pk) or plan["org"] != str(request.profile.org_id):
            raise ValidationError("Invalid merge comparison.")
        records = list(
            self.model.all_objects.select_for_update()
            .filter(org=request.profile.org, pk__in=[pk, plan["secondary"]])
            .order_by("pk")
        )
        by_id = {str(c.pk): c for c in records}
        if len(by_id) != 2:
            raise ValidationError("One record is no longer available.")
        primary, secondary = by_id[str(pk)], by_id[plan["secondary"]]
        if secondary.merged_into_id == primary.pk and not primary.merged_at:
            return Response({"id": str(primary.pk), "already_merged": True})
        if primary.merged_at or secondary.merged_at:
            raise ValidationError(
                "One record has already been merged. Refresh the comparison."
            )
        if plan["versions"] != [version(primary), version(secondary)]:
            raise ValidationError(
                "A record changed. Refresh the comparison before merging."
            )
        choices = request.data.get("choices", {})
        if not isinstance(choices, dict):
            raise ValidationError("Invalid property selections.")
        rows = self.rows(primary, secondary)
        if set(choices) - {row["key"] for row in rows}:
            raise ValidationError("Invalid property selections.")
        originals = {"primary": snapshot(primary), "secondary": snapshot(secondary)}
        values, custom = {}, dict(primary.custom_fields or {})
        for row in rows:
            selection = choices.get(row["key"], row["default"])
            if selection not in ("primary", "secondary"):
                raise ValidationError("Choose a value for each property.")
            chosen = primary if selection == "primary" else secondary
            key = row["key"]
            if key == "name" and self.model.__name__ == "Contact":
                values.update(first_name=chosen.first_name, last_name=chosen.last_name)
            elif key.startswith("custom_fields."):
                custom[key[14:]] = (chosen.custom_fields or {}).get(key[14:])
            else:
                field = self.model._meta.get_field(key)
                values[field.attname] = getattr(chosen, field.attname)
        name_key = "first_name" if self.model.__name__ == "Contact" else "name"
        if not (values.get(name_key, getattr(primary, name_key)) or "").strip():
            raise ValidationError("Name is required.")
        raw = {**values, "custom_fields": custom}
        for key in ("tags", "assigned_to", "teams"):
            raw[key] = list(
                set(getattr(primary, key).values_list("pk", flat=True))
                | set(getattr(secondary, key).values_list("pk", flat=True))
            )
        if self.model.__name__ == "Contact" and "account_id" in values:
            raw["account"] = values["account_id"]
        validate_entry(primary.org, self.model.__name__, primary, raw, raw)
        # Archive first so the secondary email or company name can be chosen safely.
        self.model.all_objects.filter(pk=secondary.pk).update(
            merged_into=primary,
            merged_at=timezone.now(),
            merge_snapshot=originals,
            is_active=False,
        )
        move_links(primary, secondary)
        # Appointments follow their Calendar records, never a manually chosen date.
        from common.models import SalesAppointment

        events = SalesAppointment.objects.filter(
            (Q(contact=primary) | Q(contacts=primary))
            if self.model.__name__ == "Contact"
            else (Q(company=primary) | Q(companies=primary)),
            org=primary.org,
            cancelled_at__isnull=True,
        ).distinct()
        if events.exists():
            values["appointment_at"] = (
                events.filter(starts_at__gte=timezone.now())
                .order_by("starts_at")
                .values_list("starts_at", flat=True)
                .first()
                or events.order_by("-starts_at")
                .values_list("starts_at", flat=True)
                .first()
            )
        previous_stage = primary.stage
        for key, value in values.items():
            setattr(primary, key, value)
        primary.custom_fields = custom
        primary.save()
        if previous_stage != primary.stage:
            self.model.objects.filter(pk=primary.pk).update(
                stage_entered_at=timezone.now()
            )
        Activity.objects.create(
            org=primary.org,
            user=request.profile,
            entity_type=self.model.__name__,
            entity_id=primary.pk,
            entity_name=primary.name[:255],
            action="UPDATE",
            description=f"Merged {self.noun}: {secondary.name}",
            metadata={
                "actor": request.user.email,
                "merge": {
                    "source_id": str(secondary.pk),
                    "primary_id": str(primary.pk),
                },
                "changes": {
                    "merge": {
                        "label": f"Merged {self.noun}",
                        "before": secondary.name,
                        "after": primary.name,
                    }
                },
            },
        )
        return Response({"id": str(primary.pk)})
