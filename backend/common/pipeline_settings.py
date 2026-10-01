"""Organization-specific labels, ordering and entry requirements for CRM stages."""

import re

from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty

from common.models import CustomFieldDefinition
from common.property_catalog import FIELDS, REQUIRED, target_model

OBJECTS = ("Contact", "Account", "Opportunity", "Task", "Case")
TERMINAL = {
    "Contact": {"QUALIFIED": 100, "NOT_QUALIFIED": 0, "LOST": 0},
    "Account": {"QUALIFIED": 100, "NOT_QUALIFIED": 0, "LOST": 0},
    "Opportunity": {"CLOSED_WON": 100, "CLOSED_LOST": 0},
    "Task": {"Completed": 100},
    "Case": {"Resolved": 100, "Closed": 100, "Rejected": 0, "Duplicate": 0},
}


def stage_field(target):
    return "status" if target in ("Task", "Case") else "stage"


def stages_for(org, target):
    model = target_model(target)
    choices = model._meta.get_field(stage_field(target)).choices
    system_keys = {key for key, _ in choices}
    from opportunity.workflow import STAGE_PROBABILITIES

    default = (
        STAGE_PROBABILITIES
        if target == "Opportunity"
        else {
            "LEAD": 0,
            "FOLLOW_UP": 50,
            "New": 0,
            "In Progress": 50,
            "Assigned": 40,
            "Pending": 60,
        }
    )
    saved = (org.pipeline_settings or {}).get(target, [])
    by_key = {s["key"]: s for s in saved}
    if target in (org.pipeline_settings or {}):
        choices = [(s["key"], s["label"]) for s in saved]
    rows = []
    for i, (key, label) in enumerate(choices):
        row = {
            "key": key,
            "label": label,
            "order": i,
            "percentage": TERMINAL[target].get(key, default.get(key, 0)),
            "required_fields": [],
            "allowed_from": [],
        }
        row.update(by_key.get(key, {}))
        row["key"] = key
        row["locked_percentage"] = False
        row["protected"] = key in system_keys
        rows.append(row)
    return sorted(rows, key=lambda s: s["order"])


def rule_properties(org, target):
    model = target_model(target)
    from common.property_catalog import LABELS, field_type

    rows = []
    for name in FIELDS[target]:
        f = model._meta.get_field(name)
        if not f.editable or name in ("created_at", "created_by", stage_field(target)):
            continue
        rows.append(
            {
                "key": name,
                "label": LABELS.get(
                    name, str(f.verbose_name).replace("_", " ").capitalize()
                ),
                "field_type": field_type(f),
                "multiple": bool(f.many_to_many),
                "relation": f.related_model.__name__ if f.is_relation else "",
                "options": [
                    {"value": key, "label": label} for key, label in (f.choices or [])
                ],
                "is_read_only": name == "appointment_at"
                and target in ("Contact", "Account"),
            }
        )
    for f in CustomFieldDefinition.objects.filter(
        org=org, target_model=target, is_active=True
    ):
        rows.append(
            {
                "key": "custom_fields." + f.key,
                "label": f.label,
                "field_type": f.field_type,
                "options": f.options or [],
            }
        )
    return rows


def validate_configuration(org, target, rows, additions=None, removals=None):
    original = stages_for(org, target)
    expected = {s["key"] for s in original}
    properties = {p["key"]: p for p in rule_properties(org, target)}
    additions, removals = additions or [], removals or {}
    if (
        not isinstance(rows, list)
        or not rows
        or any(
            not isinstance(r, dict) or not isinstance(r.get("key"), str) for r in rows
        )
    ):
        raise ValidationError("Provide at least one valid stage.")
    keys = [r["key"] for r in rows]
    if len(set(keys)) != len(keys):
        raise ValidationError("Each stage must appear only once.")
    if not isinstance(additions, list) or any(
        not isinstance(k, str) or not re.fullmatch(r"custom_[a-z0-9_]{1,25}", k)
        for k in additions
    ):
        raise ValidationError(
            "New stages need a unique internal name starting with custom_."
        )
    if (
        not isinstance(removals, dict)
        or set(keys) - expected != set(additions)
        or expected - set(keys) != set(removals)
    ):
        raise ValidationError(
            "Use add or remove stage. Existing internal names cannot change."
        )
    if any(s.get("protected") and s["key"] not in keys for s in original):
        raise ValidationError("System default stages cannot be removed.")
    if any(
        value is not None and (not isinstance(value, str) or value not in keys)
        for value in removals.values()
    ):
        raise ValidationError("Choose an existing destination for removed stages.")
    expected = set(keys)
    cleaned, names = [], set()
    for i, row in enumerate(rows):
        key, label, percentage = (
            row["key"],
            str(row.get("label", "")).strip(),
            row.get("percentage"),
        )
        if not label or len(label) > 100 or label.casefold() in names:
            raise ValidationError(
                "Stage names must be nonempty and unique (up to 100 characters)."
            )
        names.add(label.casefold())
        if type(percentage) is not int or not 0 <= percentage <= 100:
            raise ValidationError(
                "Percentage must be a whole number between 0 and 100."
            )
        required, allowed = row.get("required_fields", []), row.get("allowed_from", [])
        if not isinstance(required, list) or any(
            not isinstance(p, str) or p not in properties for p in required
        ):
            raise ValidationError("Choose existing properties for stage requirements.")
        if not isinstance(allowed, list) or any(
            not isinstance(s, str) or s not in expected or s == key for s in allowed
        ):
            raise ValidationError("Choose valid source stages.")
        cleaned.append(
            {
                "key": key,
                "label": label,
                "percentage": percentage,
                "order": i,
                "required_fields": list(dict.fromkeys(required)),
                "allowed_from": list(dict.fromkeys(allowed)),
            }
        )
    return cleaned


def validate_entry(org, target, instance, data, raw=None):
    if not org or not (org.pipeline_settings or {}).get(target):
        return
    field = stage_field(target)
    old = getattr(instance, field, None)
    new = data.get(
        field,
        old
        if instance is not None
        else target_model(target)._meta.get_field(field).get_default(),
    )
    if new == old:
        return
    rule = next((s for s in stages_for(org, target) if s["key"] == new), None)
    if not rule:
        raise ValidationError({field: "Choose an available pipeline stage."})
    if rule["allowed_from"] and old not in rule["allowed_from"]:
        raise ValidationError(
            {
                field: f"Cannot enter {rule['label']} from the current stage.",
                "stage_requirements": {
                    "code": "source_stage",
                    "stage": new,
                    "stage_label": rule["label"],
                    "message": f"This record must first be in one of these stages: {', '.join(s['label'] for s in stages_for(org, target) if s['key'] in rule['allowed_from'])}.",
                    "fields": [],
                },
            }
        )
    raw = raw or data
    aliases = {"tags": "tag_ids", "first_name": "name"}

    def value_of(key):
        if key == "appointment_at" and target in ("Contact", "Account"):
            return getattr(instance, key, None)
        if key.startswith("custom_fields."):
            import json

            values = raw.get("custom_fields", {})
            if isinstance(values, str):
                try:
                    values = json.loads(values)
                except ValueError:
                    values = {}
            if not isinstance(values, dict):
                values = {}
            return values.get(
                key[14:], (getattr(instance, "custom_fields", {}) or {}).get(key[14:])
            )
        if key in data:
            return data[key]
        if key in raw:
            return raw[key]
        if aliases.get(key) in raw:
            return raw[aliases[key]]
        value = getattr(instance, key, None)
        if hasattr(value, "all"):
            return list(value.all()) if instance and instance.pk else []
        return value

    missing = []
    properties = {p["key"]: p for p in rule_properties(org, target)}
    for key in rule["required_fields"]:
        value = value_of(key)
        if (
            value is None
            or value == []
            or (isinstance(value, str) and not value.strip())
        ):
            missing.append(
                properties.get(key, {"key": key, "label": key, "field_type": "text"})
            )
    if missing:
        message = f"To enter {rule['label']}, complete: {', '.join(p['label'] for p in missing)}."
        raise ValidationError(
            {
                field: message,
                "stage_requirements": {
                    "code": "missing_properties",
                    "stage": new,
                    "stage_label": rule["label"],
                    "message": message,
                    "fields": missing,
                },
            }
        )


class PipelineRulesMixin:
    def run_validation(self, data=empty):
        from rest_framework import serializers

        from common.record_validation import clean_record_values

        target = self.Meta.model.__name__
        data = clean_record_values(data, target)
        if hasattr(data, "get"):
            data = data.copy()
        for key in FIELDS.get(target, []):
            field = self.fields.get(key)
            if field is None or field.read_only:
                continue
            field.required = key in REQUIRED.get(target, set()) and target != "Contact"
            if isinstance(field, (serializers.CharField, serializers.ChoiceField)):
                field.allow_blank = key not in REQUIRED.get(target, set())
                field.allow_null = self.Meta.model._meta.get_field(key).null
                if (
                    not field.allow_null
                    and hasattr(data, "get")
                    and key in data
                    and data[key] is None
                ):
                    data[key] = ""
            if hasattr(field, "allow_empty"):
                field.allow_empty = True
        # Public contact name is an alias of first_name.
        if target == "Contact" and "name" in self.fields:
            self.fields["name"].required = False
            self.fields["name"].allow_blank = False
            if hasattr(data, "get") and "name" in data and data["name"] is None:
                data["name"] = ""
        if hasattr(data, "get"):
            field = stage_field(target)
            if (self.instance is None and not data.get(field)) or (
                field in data and not data.get(field)
            ):
                data = data.copy()
                data[field] = (
                    getattr(self.instance, field, None)
                    or self.Meta.model._meta.get_field(field).get_default()
                )

        org = getattr(self, "org", None) or getattr(self.instance, "org", None)
        if org:
            field = stage_field(self.Meta.model.__name__)
            if field in self.fields:
                self.fields[field].choices = [
                    (s["key"], s["label"])
                    for s in stages_for(org, self.Meta.model.__name__)
                ]
        try:
            values = super().run_validation(data)
        except ValidationError:
            if hasattr(data, "get"):
                org = getattr(self, "org", None) or getattr(self.instance, "org", None)
                validate_entry(org, self.Meta.model.__name__, self.instance, data, data)
            raise
        org = getattr(self, "org", None) or getattr(self.instance, "org", None)
        validate_entry(org, self.Meta.model.__name__, self.instance, values, data)
        return values


class PipelineMoveChoicesMixin:
    """Use the request organization's choices without mutating shared model fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request:
            self.fields[
                "column_id" if self.pipeline_target == "Opportunity" else "status"
            ].choices = [
                (s["key"], s["label"])
                for s in stages_for(request.profile.org, self.pipeline_target)
            ]
