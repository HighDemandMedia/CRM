import hashlib
import json
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from common.property_catalog import target_model
from common.pipeline_settings import stage_field
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from common.models import Org
from common.permissions import HasOrgContext, is_org_admin
from common.pipeline_settings import OBJECTS, TARGETS, stages_for, rule_properties, validate_configuration


def revision(org):
    return hashlib.sha256(json.dumps(org.pipeline_settings, sort_keys=True).encode()).hexdigest()


def pipeline_data(org, target, include_rules):
    stages = stages_for(org, target)
    if include_rules:
        field = stage_field(target)
        counts = dict(target_model(target).objects.filter(org=org).values(field).annotate(total=Count('pk')).values_list(field, 'total'))
        for stage in stages:
            stage['record_count'] = counts.get(stage['key'], 0)
    return {'stages': stages, 'properties': rule_properties(org, target) if include_rules else []}


class PipelineSettingsView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        org = request.profile.org
        return Response({'objects': [{'value': t, 'label': TARGETS[t][2]} for t in OBJECTS],
                         'pipelines': {t: pipeline_data(org, t, request.query_params.get('include_rules') != 'false') for t in OBJECTS},
                         'revision': revision(org), 'can_edit': is_org_admin(request.profile)})

    @transaction.atomic
    def put(self, request):
        if not is_org_admin(request.profile):
            return Response({'errors': 'Admin access required.'}, status=403)
        org = Org.objects.select_for_update().get(pk=request.profile.org_id)
        target = request.data.get('target_model')
        if target not in OBJECTS:
            raise ValidationError('Choose a supported object.')
        if request.data.get('revision') != revision(org):
            return Response({'errors': 'Pipeline settings changed. Reload before saving.'}, status=409)
        removals = request.data.get('removals', {})
        stages = validate_configuration(org, target, request.data.get('stages'), request.data.get('additions'), removals)
        removals = removals or {}
        field = stage_field(target)
        # Lock records as well as configuration. No record or rule is deleted until all moves validate.
        records = list(target_model(target).objects.select_for_update().filter(org=org, **{field + '__in': list(removals)}))
        if any(not removals[getattr(record, field)] for record in records):
            raise ValidationError('This stage contains records. Choose a destination before removing it.')
        org.pipeline_settings = {**org.pipeline_settings, target: stages}
        org.save(update_fields=['pipeline_settings', 'updated_at'])
        request.profile.org = org
        from contacts.serializer import CreateContactSerializer
        from accounts.serializer import AccountCreateSerializer
        from opportunity.serializer import OpportunityCreateSerializer
        from tasks.serializer import TaskCreateSerializer
        from cases.serializer import CaseCreateSerializer
        serializers = {'Contact': CreateContactSerializer, 'Account': AccountCreateSerializer, 'Opportunity': OpportunityCreateSerializer, 'Task': TaskCreateSerializer, 'Case': CaseCreateSerializer}
        pending = []
        for record in records:
            record.org = org
            destination = removals[getattr(record, field)]
            values = {field: destination}
            if target == 'Opportunity' and destination in ('CLOSED_WON', 'CLOSED_LOST') and not record.closed_on:
                values['closed_on'] = timezone.localdate()
            serializer = serializers[target](record, data=values, partial=True, request_obj=request)
            if not serializer.is_valid():
                raise ValidationError({'errors': f'Cannot move {record}. Complete its destination stage requirements first.', 'details': serializer.errors})
            pending.append(serializer)
        for serializer in pending:
            serializer.save()
        if target == 'Opportunity':
            from opportunity.models import Opportunity
            for stage in stages:
                Opportunity.objects.filter(org=org, stage=stage['key']).update(probability=stage['percentage'])
        return Response({'saved': True, 'revision': revision(org)})
