"""Organization-owned CRM role policies. Admin remains a separate protected role."""

from crum import get_current_request
from django.db import models
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError

RECORD_MODULES = ("contacts", "companies", "deals", "tasks", "tickets")
MODULES = (*RECORD_MODULES, "calendar", "reports")
SCOPES = ("none", "own", "team", "organization")
ACTIONS = (
    "view",
    "create",
    "edit",
    "stage",
    "notes",
    "attachments",
    "associations",
    "delete",
    "export",
    "reassign",
)
SCHEMA = {module: ACTIONS for module in RECORD_MODULES}
SCHEMA.update(
    calendar=(
        "view",
        "create",
        "edit",
        "cancel",
        "reassign",
        "override_conflicts",
        "export",
    ),
    reports=("view", "export"),
)
BOOLEAN_ACTIONS = ("create", "override_conflicts")
MODULE_LABELS = dict(
    contacts="Contacts",
    companies="Companies",
    deals="Deals",
    tasks="Tasks",
    tickets="Tickets",
    calendar="Calendar",
    reports="Reports",
)
ACTION_LABELS = dict(
    view="View",
    create="Create",
    edit="Edit properties",
    stage="Change stage",
    notes="Manage notes",
    attachments="Manage files",
    associations="Manage associations",
    delete="Delete records",
    export="Export",
    reassign="Assign owner",
    cancel="Cancel events",
    override_conflicts="Book conflicting times",
)
MODEL_MODULES = {
    "contacts.contact": "contacts",
    "accounts.account": "companies",
    "opportunity.opportunity": "deals",
    "tasks.task": "tasks",
    "cases.case": "tickets",
}


def default_rules(scope="own"):
    rules = {
        module: {
            action: (
                True
                if action == "create"
                else scope
                if action
                in ("view", "edit", "stage", "notes", "attachments", "associations")
                or (action == "reassign" and scope == "team")
                else "none"
            )
            for action in ACTIONS
        }
        for module in RECORD_MODULES
    }
    rules["calendar"] = {
        "view": scope,
        "create": True,
        "edit": scope,
        "cancel": "none",
        "reassign": "none",
        "override_conflicts": False,
        "export": "none",
    }
    rules["reports"] = {"view": scope, "export": "none"}
    return rules


def expanded_rules(rules, scope="own", builtin=False):
    """Preserve saved grants. New administrative/sensitive actions are never inferred."""
    result = {
        module: dict(row)
        for module, row in (rules or {}).items()
        if module in SCHEMA and isinstance(row, dict)
    }
    for module in RECORD_MODULES:
        row = result.setdefault(module, {})
        for action in ACTIONS:
            row.setdefault(
                action,
                row.get("edit", "none")
                if action in ("stage", "notes", "attachments", "associations")
                else False
                if action in BOOLEAN_ACTIONS
                else "none",
            )
    for module in ("calendar", "reports"):
        result.setdefault(
            module,
            default_rules(scope)[module]
            if builtin
            else {
                action: False if action in BOOLEAN_ACTIONS else "none"
                for action in SCHEMA[module]
            },
        )
    return result


def validate_rules(rules):
    if not isinstance(rules, dict) or set(rules) != set(MODULES):
        raise ValidationError("Supply permissions for every CRM module.")
    for module, row in rules.items():
        if not isinstance(row, dict) or set(row) != set(SCHEMA[module]):
            raise ValidationError(f"Invalid permissions for {module}.")
        for action, value in row.items():
            if action in BOOLEAN_ACTIONS:
                if not isinstance(value, bool):
                    raise ValidationError(
                        f"{module}: {action} must be enabled or disabled."
                    )
                if value and row["view"] == "none":
                    raise ValidationError(f"{module}: enable View before {action}.")
            else:
                if value not in SCOPES:
                    raise ValidationError("Invalid record scope.")
                if action != "view" and SCOPES.index(value) > SCOPES.index(row["view"]):
                    raise ValidationError(
                        f"{module}: {action} cannot exceed view access."
                    )
        for action in (
            ("stage", "notes", "attachments", "associations", "reassign")
            if module in RECORD_MODULES
            else ()
        ):
            if SCOPES.index(row[action]) > SCOPES.index(row["edit"]):
                raise ValidationError(
                    f"{module}: {action} requires Edit properties at the same level."
                )
    return rules


def policy(profile):
    if not profile or profile.role == "ADMIN" or not profile.access_role_id:
        return None
    role = profile.access_role
    # Fail closed if a corrupted or manually edited FK crosses organizations.
    return (
        expanded_rules(role.rules, role.scope, role.name in ("Member", "Manager"))
        if role.org_id == profile.org_id
        else {}
    )


def configured(profile):
    return bool(profile and profile.role != "ADMIN" and profile.access_role_id)


def scope_for(profile, module, action="view"):
    if profile.role == "ADMIN":
        return True if action in BOOLEAN_ACTIONS else "organization"
    return (
        (policy(profile) or {})
        .get(module, {})
        .get(action, False if action in BOOLEAN_ACTIONS else "none")
    )


def scoped(qs, profile, action="view", limit=None):
    """A policy scope always includes the tenant boundary. Own = current assignee; creation history never grants permanent access."""
    module = MODEL_MODULES.get(qs.model._meta.label_lower)
    qs = qs.filter(org_id=profile.org_id)
    if not module or not configured(profile):
        return qs
    scope = scope_for(profile, module, action)
    if limit is not None:
        scope = min((scope, limit), key=SCOPES.index)
    if scope == "none":
        return qs.none()
    if scope == "organization":
        return qs
    own = Q(assigned_to=profile)
    if scope == "team":
        team_ids = profile.user_teams.filter(org_id=profile.org_id).values("id")
        own |= Q(assigned_to__user_teams__in=team_ids) | Q(teams__in=team_ids)

    # A newly inserted row may be saved again before its assignees are attached.
    # This exception lasts only for its creation request, never subsequent reads.
    request = get_current_request()
    new_ids = getattr(request, "_crm_created_records", {}).get(
        qs.model._meta.label_lower, set()
    )
    if new_ids:
        own |= Q(pk__in=new_ids)
    return qs.filter(own).distinct()


def permitted(profile, obj, action="view"):
    return scoped(type(obj).objects.filter(pk=obj.pk), profile, action).exists()


def require(profile, module, action):
    if configured(profile) and scope_for(profile, module, action) in (False, "none"):
        raise PermissionDenied("Your role does not allow this action.")


# Used by the five CRM root models so side payloads, pickers, search and totals
# cannot accidentally skip the role's read scope. Worker jobs have no request
# and keep their explicit organization filters. Context belongs to crum's
# request middleware and is cleaned up when each request finishes.


class CRMRecordQuerySet(models.QuerySet):
    def _check_write(self, action):
        request = get_current_request()
        profile = getattr(request, "profile", None)
        if configured(profile):
            require(profile, MODEL_MODULES[self.model._meta.label_lower], action)
            allowed = scoped(self, profile, action).values("pk")
            if self.exclude(pk__in=allowed).exists():
                raise PermissionDenied("Some records are outside your permitted scope.")

    def update(self, **kwargs):
        self._check_write("edit")
        for field, action in (
            ("stage", "stage"),
            ("status", "stage"),
            ("description", "notes"),
        ):
            if field in kwargs and (
                field != "description"
                or MODEL_MODULES[self.model._meta.label_lower]
                in ("contacts", "companies", "deals")
            ):
                self._check_write(action)
        return super().update(**kwargs)

    def delete(self):
        self._check_write("delete")
        return super().delete()


class CRMRecordManager(models.Manager.from_queryset(CRMRecordQuerySet)):
    def get_queryset(self):
        qs = super().get_queryset()
        request = get_current_request()
        profile = getattr(request, "profile", None)
        return (
            scoped(
                qs,
                profile,
                "export"
                if request
                and (
                    request.GET.get("permission_action") == "export"
                    or "export" in request.path.strip("/").split("/")
                )
                else "view",
            )
            if configured(profile)
            else qs
        )


def check_request(request):
    """Action gate in HasOrgContext; visibility still lives in scoped querysets."""
    profile = request.profile
    if not configured(profile):
        return True
    parts = request.path.strip("/").split("/")[1:]
    root = parts[0] if parts else ""
    module = {
        "contacts": "contacts",
        "accounts": "companies",
        "opportunities": "deals",
        "tasks": "tasks",
        "cases": "tickets",
    }.get(root)
    if root == "sales-appointments":
        require(profile, "calendar", "view")
    if root == "reports":
        require(profile, "reports", "view")
    if not module:
        return True
    if any(part in ("import", "bulk", "merge", "unmerge") for part in parts[1:]):
        raise PermissionDenied(
            "Imports, bulk operations and merges are restricted to organization administrators."
        )
    action = (
        "view"
        if request.method in ("GET", "HEAD", "OPTIONS")
        else "delete"
        if request.method == "DELETE"
        else "create"
        if request.method == "POST" and len(parts) == 1
        else "edit"
    )
    if (
        request.query_params.get("permission_action") == "export"
        or "export" in parts[1:]
    ):
        action = "export"
    if (
        request.method not in ("GET", "HEAD", "OPTIONS")
        and len(parts) > 2
        and parts[1] in ("comment", "attachment")
    ):
        action = "notes" if parts[1] == "comment" else "attachments"
    require(profile, module, action)
    if action == "create" and not request.data.get("assigned_to"):
        # Default a new record to the creating member instead of leaving it invisible.
        request._full_data = request.data.copy()
        if hasattr(request._full_data, "setlist"):
            request._full_data.setlist("assigned_to", [str(profile.pk)])
        else:
            request._full_data["assigned_to"] = [str(profile.pk)]
    # Detail and sub-resource actions must respect their own action scope.
    from uuid import UUID

    from django.apps import apps

    ids = []
    for part in parts[1:]:
        try:
            ids.append(UUID(part))
        except (ValueError, TypeError):
            pass
    obj = None
    if ids:
        label = next(label for label, name in MODEL_MODULES.items() if name == module)
        model = apps.get_model(label)
        obj = model.objects.filter(pk=ids[0], org_id=profile.org_id).first()
        if len(parts) > 2 and parts[1] in ("comment", "attachment"):
            from common.models import Attachments, Comment

            child_model = Comment if parts[1] == "comment" else Attachments
            child = child_model.objects.filter(pk=ids[0], org_id=profile.org_id).first()
            obj = child.content_object if child else None
            if obj is not None and obj._meta.label_lower not in MODEL_MODULES:
                raise PermissionDenied("Invalid parent record.")
        if obj is not None and not permitted(profile, obj, action):
            raise PermissionDenied("This record is outside your permitted scope.")
    if request.method == "PUT" and obj is not None:
        # Legacy replace handlers clear M2M assignments when a field is omitted.
        # Preserve omitted owners/teams rather than letting omission bypass reassignment.
        data = request.data.copy()
        for field in ("assigned_to", "teams"):
            if field not in data:
                values = [
                    str(pk) for pk in getattr(obj, field).values_list("pk", flat=True)
                ]
                if hasattr(data, "setlist"):
                    data.setlist(field, values)
                else:
                    data[field] = values
        request._full_data = data
    if request.method in ("POST", "PUT", "PATCH"):
        validate_record_fields(request, module, obj, creating=action == "create")
        validate_assignment(request, module, obj, creating=action == "create")
    return True


def validate_assignment(request, module, obj, creating=False):
    from common.models import Profile, Teams
    from common.validators import payload_id_list

    profile = request.profile
    scope = scope_for(profile, module, "reassign")
    for field in ("assigned_to", "teams"):
        if field not in request.data:
            continue
        target = set(payload_id_list(request.data.get(field) or [], field))
        target = {str(pk) for pk in target}
        existing = (
            {str(pk) for pk in getattr(obj, field).values_list("pk", flat=True)}
            if obj
            else set()
        )
        if target == existing:
            continue
        if scope == "none":
            if creating and (
                (field == "assigned_to" and target == {str(profile.pk)})
                or (field == "teams" and not target)
            ):
                continue
            raise PermissionDenied(
                "Your permission set does not allow changing the owner or team."
            )
        team_ids = profile.user_teams.filter(org_id=profile.org_id).values("pk")
        if field == "assigned_to":
            allowed = Profile.objects.filter(org_id=profile.org_id, is_active=True)
            if scope == "team":
                allowed = allowed.filter(Q(pk=profile.pk) | Q(user_teams__in=team_ids))
            elif scope == "own":
                allowed = allowed.filter(pk=profile.pk)
        else:
            allowed = Teams.objects.filter(org_id=profile.org_id)
            if scope != "organization":
                allowed = (
                    allowed.filter(pk__in=team_ids)
                    if scope == "team"
                    else allowed.none()
                )
        if not target.issubset(
            {str(pk) for pk in allowed.values_list("pk", flat=True)}
        ):
            raise PermissionDenied(
                "Choose an owner or team within your permitted scope."
            )


def ensure_default_roles(org):
    from common.models import CRMRole

    member, _ = CRMRole.objects.get_or_create(
        org=org,
        name="Member",
        defaults={
            "scope": "own",
            "description": "Own CRM records",
            "rules": default_rules("own"),
        },
    )
    manager, _ = CRMRole.objects.get_or_create(
        org=org,
        name="Manager",
        defaults={
            "scope": "team",
            "description": "Team CRM records",
            "rules": default_rules("team"),
        },
    )
    return member, manager


def assert_model_write(obj, action):
    module = MODEL_MODULES.get(obj._meta.label_lower)
    if not module:
        return
    profile = getattr(get_current_request(), "profile", None)
    if not configured(profile):
        return
    require(profile, module, action)
    if obj.org_id != profile.org_id or (
        action != "create" and not permitted(profile, obj, action)
    ):
        raise PermissionDenied("This record is outside your permitted scope.")
    if action == "edit":
        old = type(obj)._base_manager.filter(pk=obj.pk, org_id=profile.org_id).first()
        if old is not None:
            for field, permission in (
                ("stage", "stage"),
                ("status", "stage"),
                ("description", "notes"),
            ):
                if field == "description" and module not in (
                    "contacts",
                    "companies",
                    "deals",
                ):
                    continue
                if hasattr(obj, field) and getattr(obj, field) != getattr(old, field):
                    require_record(profile, obj, permission)
    if action == "create":
        request = get_current_request()
        if not hasattr(request, "_crm_created_records"):
            request._crm_created_records = {}
        request._crm_created_records.setdefault(obj._meta.label_lower, set()).add(
            obj.pk
        )


class VisibleCRMSerializerMixin:
    """Foreign-key nesting uses base managers; check visibility before rendering."""

    def to_representation(self, instance):
        profile = getattr(get_current_request(), "profile", None)
        label = getattr(getattr(instance, "_meta", None), "label_lower", None)
        if (
            label in MODEL_MODULES
            and configured(profile)
            and not permitted(profile, instance)
        ):
            return None
        return super().to_representation(instance)


def require_record(profile, obj, action="edit"):
    if configured(profile) and not permitted(profile, obj, action):
        raise PermissionDenied(
            f"Your permission set does not allow {ACTION_LABELS.get(action, action).lower()} on this record."
        )


def validate_record_fields(request, module, obj, creating=False):
    """Specific capabilities also apply to writes through ordinary edit forms."""
    if not configured(request.profile):
        return

    def gate(action):
        require(request.profile, module, action)
        if obj is not None:
            require_record(request.profile, obj, action)

    fields = {
        "stage": "stage",
        "status": "stage",
        "stage_id": "stage",
        "description": "notes",
        "account": "associations",
        "contacts": "associations",
        "companies": "associations",
        "contact": "associations",
    }
    for field, action in fields.items():
        if field == "description" and module not in ("contacts", "companies", "deals"):
            continue
        if field not in request.data:
            continue
        raw = request.data.get(field)
        if creating and action == "stage":
            continue  # Initial stage belongs to Create; entry rules still apply.
        if obj is not None and hasattr(obj, field):
            value = getattr(obj, field)
            if hasattr(value, "values_list"):
                from common.validators import payload_id_list

                if set(map(str, value.values_list("pk", flat=True))) == set(
                    map(str, payload_id_list(raw or [], field))
                ):
                    continue
            elif str(getattr(value, "pk", value) or "") == str(raw or ""):
                continue
        elif not raw:
            continue
        gate(action)
    if "move" in request.path.strip("/").split("/"):
        gate("stage")
    if "associations" in request.path.strip("/").split("/"):
        gate("associations")
    if request.data.get("comment"):
        gate("notes")
    if any("attachment" in name for name in request.FILES):
        gate("attachments")


def calendar_scoped(qs, profile, action="view", limit=None):
    qs = qs.filter(org_id=profile.org_id)
    if profile.role == "ADMIN":
        return qs
    scope = scope_for(profile, "calendar", action) if configured(profile) else "own"
    if limit is not None:
        scope = min((scope, limit), key=SCOPES.index)
    if scope == "none":
        return qs.none()
    if scope == "organization":
        return qs
    visible = Q(host=profile)
    if action in ("view", "export"):
        visible |= Q(attendee_users=profile)
    if scope == "team":
        team_ids = profile.user_teams.filter(org_id=profile.org_id).values("pk")
        visible |= Q(host__user_teams__in=team_ids)
    return qs.filter(visible).distinct()


def calendar_hosts(profile):
    from common.models import Profile

    qs = Profile.objects.filter(
        org_id=profile.org_id, is_active=True, user__is_active=True
    )
    if profile.role == "ADMIN":
        return qs
    scope = scope_for(profile, "calendar", "reassign") if configured(profile) else "own"
    if scope == "organization":
        return qs
    if scope == "team":
        teams = profile.user_teams.filter(org_id=profile.org_id).values("pk")
        return qs.filter(Q(pk=profile.pk) | Q(user_teams__in=teams)).distinct()
    return qs.filter(pk=profile.pk)


def activity_scoped(qs, profile):
    """An activity must not reveal a record hidden from lists/search/reports."""
    from django.apps import apps

    qs = qs.filter(org_id=profile.org_id)
    if not configured(profile):
        return qs
    allowed = Q(pk__in=[])
    for label in MODEL_MODULES:
        model = apps.get_model(label)
        allowed |= Q(
            entity_type=model.__name__,
            entity_id__in=scoped(model._base_manager.all(), profile).values("pk"),
        )
    return qs.filter(allowed)
