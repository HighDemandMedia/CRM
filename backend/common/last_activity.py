"""Last recorded property change, shared by the five CRM objects."""
from django.db.models import OuterRef, Subquery
from django.db.models.functions import Coalesce
from rest_framework import serializers

CHANGE_ACTIONS = ('CREATE', 'UPDATE', 'ASSIGN', 'STATUS_CHANGED', 'PRIORITY_CHANGED',
                  'ROUTED', 'REOPENED', 'LINKED_PARENT', 'UNLINKED_PARENT',
                  'MERGED', 'MERGE_TARGET', 'UNMERGED', 'UNMERGE_TARGET')


def with_last_activity(queryset):
    from common.models import Activity
    if 'last_activity_at' in queryset.query.annotations:
        return queryset
    latest = Activity.objects.filter(
        org_id=OuterRef('org_id'), entity_type=queryset.model.__name__,
        entity_id=OuterRef('pk'), action__in=CHANGE_ACTIONS,
    ).order_by('-created_at').values('created_at')[:1]
    return queryset.annotate(last_activity_at=Coalesce(Subquery(latest), 'created_at'))


class ActivityListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        # Lists are evaluated once, with one aggregate lookup for the entire page.
        from django.db.models import Max
        from common.models import Activity
        records = list(data.all() if hasattr(data, 'all') else data)
        missing = [row for row in records if not hasattr(row, 'last_activity_at')]
        if missing:
            rows = Activity.objects.filter(
                org_id__in={row.org_id for row in missing},
                entity_type=missing[0].__class__.__name__,
                entity_id__in=[row.pk for row in missing], action__in=CHANGE_ACTIONS,
            ).values('org_id', 'entity_id').annotate(latest=Max('created_at'))
            latest = {(row['org_id'], row['entity_id']): row['latest'] for row in rows}
            for row in missing:
                row.last_activity_at = latest.get((row.org_id, row.pk), row.created_at)
        return super().to_representation(records)


class LastActivitySerializerMixin:
    def get_fields(self):
        fields = super().get_fields()
        fields['last_activity_at'] = serializers.DateTimeField(read_only=True)
        return fields

    def to_representation(self, instance):
        if not hasattr(instance, 'last_activity_at'):
            from common.models import Activity
            instance.last_activity_at = Activity.objects.filter(
                org_id=instance.org_id, entity_type=instance.__class__.__name__,
                entity_id=instance.pk, action__in=CHANGE_ACTIONS,
            ).order_by('-created_at').values_list('created_at', flat=True).first() or instance.created_at
        return super().to_representation(instance)
