"""Organization-owned manual record creation layouts, separate from stage rules."""

import hashlib
import json

from rest_framework.exceptions import ValidationError

from common.models import CustomFieldDefinition
from common.property_catalog import FIELDS, LABELS, field_type, target_model

IDENTITY = {
    "Contact": "first_name",
    "Account": "name",
    "Opportunity": "name",
    "Task": "title",
    "Case": "name",
}
EXCLUDED = {"id", "created_at", "created_by", "last_activity_at", "appointment_at"}
RELATIONS = {"account", "contacts", "opportunity", "case"}


def catalog(org, target):
    if not isinstance(target, str) or target not in IDENTITY:
        raise ValidationError("Choose a supported object.")
    model = target_model(target)
    keys = [key for key in FIELDS[target] if key not in EXCLUDED]
    if target in {"Contact", "Account", "Opportunity"}:
        keys.append("description")
    if target == "Contact":
        keys.append("account")
    # Deals use the organization's currency, not a per-record choice.
    if target == "Opportunity":
        keys.remove("currency")
    rows = []
    for key in keys:
        f = model._meta.get_field(key)
        section = (
            "Identity"
            if key in {IDENTITY[target], "email", "phone", "website"}
            else "Ownership"
            if key == "assigned_to"
            else "Associations"
            if key in RELATIONS
            else "Additional details"
        )
        rows.append(
            {
                "key": key,
                "label": LABELS.get(
                    key, str(f.verbose_name).replace("_", " ").capitalize()
                ),
                "field_type": "phone"
                if key == "phone"
                else "integer"
                if key in {"reminder_days", "number_of_employees"}
                else field_type(f),
                "relation": f.related_model.__name__ if f.is_relation else "",
                "multiple": bool(f.many_to_many)
                and (key != "assigned_to" or target == "Task"),
                "options": [
                    {"value": value, "label": str(label)}
                    for value, label in (f.choices or [])
                ],
                "max_length": getattr(f, "max_length", None),
                "locked": key == IDENTITY[target],
                "section": section,
                "custom": False,
            }
        )
    rows.sort(
        key=lambda row: [
            "Identity",
            "Ownership",
            "Associations",
            "Additional details",
        ].index(row["section"])
    )
    for definition in CustomFieldDefinition.objects.filter(
        org=org, target_model=target, is_active=True
    ):
        rows.append(
            {
                "key": "custom_fields." + definition.key,
                "label": definition.label,
                "field_type": definition.field_type,
                "options": definition.options or [],
                "multiple": definition.field_type == "multi_select",
                "relation": "",
                "locked": False,
                "section": "Additional details",
                "custom": True,
            }
        )
    return rows


def configuration(org, target):
    fields = catalog(org, target)
    allowed = {field["key"]: field for field in fields}
    saved = (org.creation_forms or {}).get(target)
    if saved is None:
        saved = [
            {"key": f["key"], "required": f["locked"]}
            for f in fields
            if not f["custom"]
        ]
    # Disabled/deleted definitions are omitted without deleting stored record values.
    selected = [
        {
            **allowed[row["key"]],
            "required": bool(row["required"] or allowed[row["key"]]["locked"]),
        }
        for row in saved
        if row["key"] in allowed
    ]
    for field in fields:
        if field["locked"] and not any(row["key"] == field["key"] for row in selected):
            selected.insert(0, {**field, "required": True})
    digest = hashlib.sha256(
        json.dumps({"saved": saved, "fields": fields}, sort_keys=True).encode()
    ).hexdigest()
    return {
        "target_model": target,
        "fields": fields,
        "selected": selected,
        "revision": digest,
    }


def validate_configuration(org, target, selected):
    allowed = {row["key"]: row for row in catalog(org, target)}
    if not isinstance(selected, list) or len(selected) > len(allowed):
        raise ValidationError("Choose valid creation fields.")
    keys = []
    for row in selected:
        if (
            not isinstance(row, dict)
            or set(row) != {"key", "required"}
            or not isinstance(row.get("key"), str)
            or row["key"] not in allowed
            or type(row.get("required")) is not bool
        ):
            raise ValidationError("Choose valid properties and required flags.")
        keys.append(row["key"])
    if len(keys) != len(set(keys)):
        raise ValidationError("Include each property only once.")
    for field in allowed.values():
        if field["locked"] and not any(
            r["key"] == field["key"] and r["required"] for r in selected
        ):
            raise ValidationError(
                "The identifying field must stay visible and required."
            )
    if (
        target == "Task"
        and sum(
            r["required"] and r["key"] in {"account", "opportunity", "case"}
            for r in selected
        )
        > 1
    ):
        raise ValidationError(
            "A task can have only one parent object. Require at most one parent type."
        )
    if any(r["key"] == "reminder_days" and r["required"] for r in selected) and not any(
        r["key"] == "due_date" and r["required"] for r in selected
    ):
        raise ValidationError("A required reminder also needs a required due date.")
    return selected


def add_property(org, target, key):
    selected = [
        {"key": f["key"], "required": f["required"]}
        for f in configuration(org, target)["selected"]
    ]
    if not any(f["key"] == key for f in selected):
        selected.append({"key": key, "required": False})
    org.creation_forms = {**(org.creation_forms or {}), target: selected}
    org.save(update_fields=["creation_forms", "updated_at"])


def _present(value):
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None and value != [] and value != {}


def validate_creation(org, target, data):
    """Only called by authenticated record POSTs, never edits or public web forms."""
    custom = data.get("custom_fields", {})
    if isinstance(custom, str):
        try:
            custom = json.loads(custom)
        except (ValueError, TypeError):
            raise ValidationError({"custom_fields": "Enter valid property values."})
    if not isinstance(custom, dict):
        raise ValidationError({"custom_fields": "Enter a property object."})
    errors = {}
    for field in configuration(org, target)["selected"]:
        if not field["required"]:
            continue
        key = field["key"]
        if field["custom"]:
            value = custom.get(key.removeprefix("custom_fields."))
        else:
            value = data.get(
                "name"
                if target == "Contact" and key == "first_name" and "name" in data
                else key
            )
            if key == "tags" and "tag_ids" in data:
                value = data["tag_ids"]
        if not _present(value):
            errors[key] = f"{field['label']} is required when creating this record."
    if errors:
        raise ValidationError(errors)
