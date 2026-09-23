"""Organization-owned CRM role policies. Admin remains a separate protected role."""
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError

MODULES = ('contacts', 'companies', 'deals', 'tasks', 'tickets')
SCOPES = ('none', 'own', 'team', 'organization')
ACTIONS = ('view', 'create', 'edit', 'delete', 'export', 'reassign')
MODEL_MODULES = {'contacts.contact':'contacts', 'accounts.account':'companies', 'opportunity.opportunity':'deals', 'tasks.task':'tasks', 'cases.case':'tickets'}

def default_rules(scope='own'):
    return {module: {'view':scope, 'create':True, 'edit':scope, 'delete':'none', 'export':'none', 'reassign':'team' if scope == 'team' else 'none'} for module in MODULES}

def validate_rules(rules):
    if not isinstance(rules, dict) or set(rules) != set(MODULES):
        raise ValidationError('Supply permissions for every CRM module.')
    for module, row in rules.items():
        if isinstance(row, dict):
            row.setdefault('reassign', 'none')
        if not isinstance(row, dict) or set(row) != set(ACTIONS):
            raise ValidationError(f'Invalid permissions for {module}.')
        if not isinstance(row['create'], bool):
            raise ValidationError('Create must be true or false.')
        for action in ('view', 'edit', 'delete', 'export', 'reassign'):
            if row[action] not in SCOPES:
                raise ValidationError('Invalid record scope.')
            if action != 'view' and SCOPES.index(row[action]) > SCOPES.index(row['view']):
                raise ValidationError(f'{module}: {action} cannot exceed view access.')
    return rules

def policy(profile):
    if not profile or profile.role == 'ADMIN' or not profile.access_role_id:
        return None
    role = profile.access_role
    # Fail closed if a corrupted or manually edited FK crosses organizations.
    return role.rules if role.org_id == profile.org_id else {}

def configured(profile):
    return bool(profile and profile.role != 'ADMIN' and profile.access_role_id)

def scope_for(profile, module, action='view'):
    if profile.role == 'ADMIN':
        return True if action == 'create' else 'organization'
    return (policy(profile) or {}).get(module, {}).get(action, False if action == 'create' else 'none')

def scoped(qs, profile, action='view'):
    """A policy scope always includes the tenant boundary. Own = current assignee; creation history never grants permanent access."""
    module = MODEL_MODULES.get(qs.model._meta.label_lower)
    qs = qs.filter(org_id=profile.org_id)
    if not module or not configured(profile):
        return qs
    scope = scope_for(profile, module, action)
    if scope == 'none':
        return qs.none()
    if scope == 'organization':
        return qs
    own = Q(assigned_to=profile)
    if scope == 'team':
        team_ids = profile.user_teams.filter(org_id=profile.org_id).values('id')
        own |= Q(assigned_to__user_teams__in=team_ids) | Q(teams__in=team_ids)

    # A newly inserted row may be saved again before its assignees are attached.
    # This exception lasts only for its creation request, never subsequent reads.
    request = get_current_request()
    new_ids = getattr(request, '_crm_created_records', {}).get(qs.model._meta.label_lower, set())
    if new_ids:
        own |= Q(pk__in=new_ids)
    return qs.filter(own).distinct()

def permitted(profile, obj, action='view'):
    return scoped(type(obj).objects.filter(pk=obj.pk), profile, action).exists()

def require(profile, module, action):
    if configured(profile) and scope_for(profile, module, action) in (False, 'none'):
        raise PermissionDenied('Your role does not allow this action.')

# Used by the five CRM root models so side payloads, pickers, search and totals
# cannot accidentally skip the role's read scope. Worker jobs have no request
# and keep their explicit organization filters. Context belongs to crum's
# request middleware and is cleaned up when each request finishes.
from django.db import models
from crum import get_current_request

class CRMRecordQuerySet(models.QuerySet):
    def _check_write(self, action):
        request = get_current_request()
        profile = getattr(request, 'profile', None)
        if configured(profile):
            require(profile, MODEL_MODULES[self.model._meta.label_lower], action)
            allowed = scoped(self, profile, action).values('pk')
            if self.exclude(pk__in=allowed).exists():
                raise PermissionDenied('Some records are outside your permitted scope.')
    def update(self, **kwargs):
        self._check_write('edit')
        return super().update(**kwargs)
    def delete(self):
        self._check_write('delete')
        return super().delete()

class CRMRecordManager(models.Manager.from_queryset(CRMRecordQuerySet)):
    def get_queryset(self):
        qs = super().get_queryset()
        request = get_current_request()
        profile = getattr(request, 'profile', None)
        return scoped(qs, profile, 'export' if request and (request.GET.get('permission_action') == 'export' or 'export' in request.path.strip('/').split('/')) else 'view') if configured(profile) else qs


def check_request(request):
    """Action gate in HasOrgContext; visibility still lives in scoped querysets."""
    profile = request.profile
    if not configured(profile):
        return True
    parts = request.path.strip('/').split('/')[1:]
    root = parts[0] if parts else ''
    module = {'contacts':'contacts', 'accounts':'companies', 'opportunities':'deals', 'tasks':'tasks', 'cases':'tickets'}.get(root)
    if not module:
        return True
    action = 'view' if request.method in ('GET','HEAD','OPTIONS') else 'delete' if request.method == 'DELETE' else 'create' if request.method == 'POST' and len(parts) == 1 else 'edit'
    if request.query_params.get('permission_action') == 'export' or 'export' in parts[1:]:
        action = 'export'
    require(profile, module, action)
    if action == 'create' and not request.data.get('assigned_to'):
        # Default a new record to the creating member instead of leaving it invisible.
        request._full_data = request.data.copy()
        if hasattr(request._full_data, 'setlist'):
            request._full_data.setlist('assigned_to', [str(profile.pk)])
        else:
            request._full_data['assigned_to'] = [str(profile.pk)]
    # Detail and sub-resource actions must respect their own action scope.
    from uuid import UUID
    from django.apps import apps
    ids = []
    for part in parts[1:]:
        try: ids.append(UUID(part))
        except (ValueError, TypeError): pass
    obj = None
    if ids:
        label = next(label for label, name in MODEL_MODULES.items() if name == module)
        model = apps.get_model(label)
        obj = model.objects.filter(pk=ids[0], org_id=profile.org_id).first()
        if len(parts) > 2 and parts[1] in ('comment', 'attachment'):
            from common.models import Comment, Attachments
            child_model = Comment if parts[1] == 'comment' else Attachments
            child = child_model.objects.filter(pk=ids[0],org_id=profile.org_id).first()
            obj = child.content_object if child else None
            if obj is not None and obj._meta.label_lower not in MODEL_MODULES:
                raise PermissionDenied('Invalid parent record.')
        if obj is not None and not permitted(profile, obj, action):
            raise PermissionDenied('This record is outside your permitted scope.')
    if request.method == 'PUT' and obj is not None:
        # Legacy replace handlers clear M2M assignments when a field is omitted.
        # Preserve omitted owners/teams rather than letting omission bypass reassignment.
        data = request.data.copy()
        for field in ('assigned_to', 'teams'):
            if field not in data:
                values = [str(pk) for pk in getattr(obj, field).values_list('pk', flat=True)]
                if hasattr(data, 'setlist'):
                    data.setlist(field, values)
                else:
                    data[field] = values
        request._full_data = data
    if request.method in ('POST', 'PUT', 'PATCH'):
        validate_assignment(request, module, obj, creating=action == 'create')
    return True


def validate_assignment(request, module, obj, creating=False):
    from common.models import Profile, Teams
    from common.validators import payload_id_list
    profile = request.profile
    scope = scope_for(profile, module, 'reassign')
    for field in ('assigned_to', 'teams'):
        if field not in request.data:
            continue
        target = set(payload_id_list(request.data.get(field) or [], field))
        target = {str(pk) for pk in target}
        existing = {str(pk) for pk in getattr(obj, field).values_list('pk', flat=True)} if obj else set()
        if target == existing:
            continue
        if scope == 'none':
            if creating and ((field == 'assigned_to' and target == {str(profile.pk)}) or (field == 'teams' and not target)):
                continue
            raise PermissionDenied('Your permission set does not allow changing the owner or team.')
        team_ids = profile.user_teams.filter(org_id=profile.org_id).values('pk')
        if field == 'assigned_to':
            allowed = Profile.objects.filter(org_id=profile.org_id, is_active=True)
            if scope == 'team':
                allowed = allowed.filter(Q(pk=profile.pk) | Q(user_teams__in=team_ids))
            elif scope == 'own':
                allowed = allowed.filter(pk=profile.pk)
        else:
            allowed = Teams.objects.filter(org_id=profile.org_id)
            if scope != 'organization':
                allowed = allowed.filter(pk__in=team_ids) if scope == 'team' else allowed.none()
        if not target.issubset({str(pk) for pk in allowed.values_list('pk', flat=True)}):
            raise PermissionDenied('Choose an owner or team within your permitted scope.')


def ensure_default_roles(org):
    from common.models import CRMRole
    member, _ = CRMRole.objects.get_or_create(org=org, name='Member', defaults={'scope':'own', 'description':'Own CRM records', 'rules':default_rules('own')})
    manager, _ = CRMRole.objects.get_or_create(org=org, name='Manager', defaults={'scope':'team', 'description':'Team CRM records', 'rules':default_rules('team')})
    return member, manager


def assert_model_write(obj, action):
    module = MODEL_MODULES.get(obj._meta.label_lower)
    if not module: return
    profile = getattr(get_current_request(), 'profile', None)
    if not configured(profile): return
    require(profile, module, action)
    if obj.org_id != profile.org_id or (action != 'create' and not permitted(profile,obj,action)):
        raise PermissionDenied('This record is outside your permitted scope.')
    if action == 'create':
        request = get_current_request()
        if not hasattr(request, '_crm_created_records'):
            request._crm_created_records = {}
        request._crm_created_records.setdefault(obj._meta.label_lower, set()).add(obj.pk)


class VisibleCRMSerializerMixin:
    """Foreign-key nesting uses base managers; check visibility before rendering."""
    def to_representation(self, instance):
        profile = getattr(get_current_request(), 'profile', None)
        label = getattr(getattr(instance, '_meta', None), 'label_lower', None)
        if label in MODEL_MODULES and configured(profile) and not permitted(profile, instance):
            return None
        return super().to_representation(instance)
