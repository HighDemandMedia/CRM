from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import serializers

from common.last_activity import (
    ActivityListSerializer,
    LastActivitySerializerMixin,
    with_last_activity,
)
from common.models import Activity
from common.property_catalog import properties_for, target_model


@pytest.mark.django_db
@pytest.mark.parametrize(
    "target", ["Contact", "Account", "Opportunity", "Task", "Case"]
)
def test_last_activity_is_read_only_scoped_and_ignores_views(
    target, org_a, org_b, django_assert_num_queries
):
    model = target_model(target)
    record = model.objects.create(
        org=org_a,
        **(
            {"title": "Activity test", "status": "New", "priority": "Medium"}
            if target == "Task"
            else {}
        ),
    )
    earlier = timezone.now() - timedelta(days=2)
    model.objects.filter(pk=record.pk).update(
        created_at=earlier, updated_at=timezone.now()
    )
    record.refresh_from_db()
    Activity.objects.filter(org=org_a, entity_id=record.pk).update(created_at=earlier)
    changed = earlier + timedelta(hours=1)
    activity = Activity.objects.create(
        org=org_a, entity_type=target, entity_id=record.pk, action="UPDATE"
    )
    Activity.objects.filter(pk=activity.pk).update(created_at=changed)
    Activity.objects.create(
        org=org_a, entity_type=target, entity_id=record.pk, action="VIEW"
    )
    Activity.objects.create(
        org=org_b, entity_type=target, entity_id=record.pk, action="UPDATE"
    )
    Activity.objects.create(
        org=org_a, entity_type=target, entity_id=record.pk, action="COMMENT"
    )

    class RecordSerializer(LastActivitySerializerMixin, serializers.ModelSerializer):
        class Meta:
            fields = ["id"]
            list_serializer_class = ActivityListSerializer

    RecordSerializer.Meta.model = model
    assert RecordSerializer(record).fields["last_activity_at"].read_only
    from django.utils.dateparse import parse_datetime

    assert parse_datetime(RecordSerializer(record).data["last_activity_at"]) == changed
    records = [model.objects.get(pk=record.pk), model.objects.get(pk=record.pk)]
    with django_assert_num_queries(1):
        payload = RecordSerializer(records, many=True).data
    assert parse_datetime(payload[0]["last_activity_at"]) == changed
    assert (
        with_last_activity(model.objects.filter(pk=record.pk)).get().last_activity_at
        == changed
    )
    from importlib import import_module

    module, cls = {
        "Contact": ("contacts", "ContactSerializer"),
        "Account": ("accounts", "AccountSerializer"),
        "Opportunity": ("opportunity", "OpportunitySerializer"),
        "Task": ("tasks", "TaskListSerializer"),
        "Case": ("cases", "CaseSerializer"),
    }[target]
    actual = getattr(import_module(f"{module}.serializer"), cls)
    assert (
        parse_datetime(
            actual(model.objects.filter(pk=record.pk), many=True).data[0][
                "last_activity_at"
            ]
        )
        == changed
    )
    assert next(
        p
        for p in properties_for(org_a, target, [])["properties"]
        if p["key"] == "last_activity_at"
    )["is_system"]


@pytest.mark.django_db
def test_no_change_uses_creation_date(org_a):
    from contacts.models import Contact

    record = Contact.objects.create(org=org_a)
    Activity.objects.filter(entity_id=record.pk).delete()
    assert (
        with_last_activity(Contact.objects.filter(pk=record.pk)).get().last_activity_at
        == record.created_at
    )
