"""Read-only catalog of CRM properties, with tenant-scoped usage counts."""

from django.apps import apps
from django.db import models
from django.db.models import Count, Q

TARGETS = {
    "Contact": ("contacts", "Contact", "Contacts"),
    "Account": ("accounts", "Account", "Companies"),
    "Opportunity": ("opportunity", "Opportunity", "Deals"),
    "Task": ("tasks", "Task", "Tasks"),
    "Case": ("cases", "Case", "Tickets"),
    "Lead": ("leads", "Lead", "Leads"),
    "Estimate": ("invoices", "Estimate", "Estimates"),
    "Invoice": ("invoices", "Invoice", "Invoices"),
    "RecurringInvoice": ("invoices", "RecurringInvoice", "Recurring invoices"),
}
ADDRESS = "address_line city state postcode country".split()
# The fields exposed by the adapted CRM, rather than legacy/internal columns.
FIELDS = {
    "Contact": "first_name phone email source stage assigned_to language preferred_communication_channel appointment_at".split()
    + ADDRESS
    + ["tags", "created_at", "created_by"],
    "Account": "name website assigned_to phone email industry number_of_employees annual_revenue currency source stage language preferred_communication_channel appointment_at".split()
    + ADDRESS
    + ["pages", "tags", "contacts", "created_at", "created_by"],
    "Opportunity": "name amount currency stage closed_on assigned_to priority lead_source phone email language".split()
    + ADDRESS
    + ["tags", "contacts", "account", "created_at", "created_by"],
    "Task": "title status priority assigned_to due_date reminder_days description account contacts opportunity case created_at created_by".split(),
    "Case": "name status priority category source assigned_to due_at waiting_reason resolution_note description account contacts created_at created_by".split(),
}
for _target in FIELDS:
    FIELDS[_target].insert(0, "id")
REQUIRED = {
    target: {
        "id",
        "first_name"
        if target == "Contact"
        else "title"
        if target == "Task"
        else "name",
    }
    for target in FIELDS
}
LABELS = {
    "id": "Record ID",
    "first_name": "Name",
    "name": "Name",
    "title": "Name",
    "assigned_to": "Owner",
    "website": "Domain",
    "closed_on": "Close date",
    "lead_source": "Source",
    "address_line": "Address",
    "postcode": "Zip code",
    "account": "Company",
    "contacts": "Contacts",
    "opportunity": "Deal",
    "case": "Ticket",
    "due_at": "Due date",
    "reminder_days": "Reminder",
    "description": "Notes",
    "appointment_at": "Appointment",
}


def target_model(target):
    ref = TARGETS.get(target)
    return apps.get_model(*ref[:2]) if ref else None


def field_type(field):
    if field.many_to_many:
        return "multi_select"
    if field.is_relation:
        return "relationship"
    if field.choices:
        return "dropdown"
    for cls, label in (
        (models.UUIDField, "uuid"),
        (models.EmailField, "email"),
        (models.URLField, "url"),
        (models.BooleanField, "checkbox"),
        (models.DateTimeField, "datetime"),
        (models.DateField, "date"),
        (models.TextField, "textarea"),
        (models.DecimalField, "number"),
        (models.IntegerField, "number"),
        (models.FloatField, "number"),
        (models.JSONField, "list"),
    ):
        if isinstance(field, cls):
            return label
    return "text"


def properties_for(org, target, definitions):
    model = target_model(target)
    qs = model.objects.filter(org=org)
    allowed = FIELDS.get(target)
    fields = [
        f
        for f in model._meta.get_fields()
        if not f.auto_created
        and (
            f.name in allowed
            if allowed is not None
            else f.name
            not in {
                "id",
                "org",
                "custom_fields",
                "is_sample",
                "is_active",
                "updated_at",
            }
        )
    ]
    if allowed:
        fields.sort(key=lambda f: allowed.index(f.name))
    # Aggregate scalar properties together; keep M2M joins separate to avoid
    # multiplying rows when several associations are populated on one record.
    counts, scalar = {}, {}
    for field in fields:
        key = field.name
        condition = Q(**{f"{key}__isnull": False})
        if isinstance(field, (models.CharField, models.TextField)):
            condition &= ~Q(**{key: ""})
        if isinstance(field, models.JSONField):
            condition &= ~Q(**{key: []}) & ~Q(**{key: {}})
        if field.many_to_many:
            counts[key] = qs.filter(condition).values("pk").distinct().count()
        else:
            scalar[key] = Count("pk", filter=condition)
    counts.update(qs.aggregate(**scalar))
    total = qs.count()
    rows = []
    for field in fields:
        key = field.name
        label = LABELS.get(key, str(field.verbose_name).replace("_", " ").capitalize())
        if key == "assigned_to" and target in {"Task", "Case"}:
            label = "Assigned to"
        rows.append(
            {
                "id": f"system:{target}:{key}",
                "key": key,
                "label": label,
                "target_model": target,
                "field_type": "dropdown"
                if key == "assigned_to" and target != "Task"
                else "phone"
                if key == "phone"
                else field_type(field),
                "is_system": True,
                "is_active": True,
                "is_required": key in REQUIRED.get(target, set())
                if target in REQUIRED
                else not field.blank and not field.null and field.editable,
                "usage_count": counts.get(key, 0),
                "is_read_only": not field.editable or key == "appointment_at",
                "requirement_note": "Generated automatically"
                if key == "id"
                else "Managed in Calendar"
                if key == "appointment_at"
                else "",
            }
        )
    if target in FIELDS:
        rows.append(
            {
                "id": f"system:{target}:last_activity_at",
                "key": "last_activity_at",
                "label": "Last Activity",
                "target_model": target,
                "field_type": "datetime",
                "is_system": True,
                "is_active": True,
                "is_required": False,
                "is_read_only": True,
                "usage_count": total,
                "requirement_note": "Automatically records the latest property change.",
            }
        )
    if definitions:
        aggregates = {}
        for i, definition in enumerate(definitions):
            path = f"custom_fields__{definition['key']}"
            # False and zero ARE values. Null/empty strings are not.
            condition = (
                Q(**{"custom_fields__has_key": definition["key"]})
                & ~Q(**{path: None})
                & ~Q(**{path: ""})
                & ~Q(**{path: []})
            )
            aggregates[f"c{i}"] = Count("pk", filter=condition)
        usage = qs.aggregate(**aggregates)
        for i, definition in enumerate(definitions):
            rows.append(
                {
                    **definition,
                    **({"is_required": False} if target in FIELDS else {}),
                    "is_system": False,
                    "usage_count": usage[f"c{i}"],
                }
            )
    from common.property_layout import ordered_properties, revision

    rows = ordered_properties(org, target, rows)
    return {
        "revision": revision(org),
        "properties": rows,
        "target_model": target,
        "record_count": total,
        "objects": [
            {"value": key, "label": value[2]} for key, value in TARGETS.items()
        ],
    }
