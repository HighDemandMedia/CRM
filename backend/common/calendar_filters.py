from datetime import timedelta
from rest_framework import serializers


def filter_calendar(queryset, params):
    if not params.get("calendar_start") and not params.get("calendar_end"):
        return queryset
    field = serializers.DateTimeField()
    start = field.run_validation(params.get("calendar_start"))
    end = field.run_validation(params.get("calendar_end"))
    if end <= start or end - start > timedelta(days=43):
        raise serializers.ValidationError("Invalid calendar range.")
    return queryset.filter(appointment_at__gte=start, appointment_at__lt=end)
