"""Bounded board reads over the list view's already filtered/authorized queryset."""
from django.db.models import Count

from common.pipeline_settings import stages_for


def bounded_int(value, default, maximum):
    try:
        return min(max(int(value), 0), maximum)
    except (TypeError, ValueError):
        return default


def pipeline_board(queryset, request, serializer_class, totals, *, context=None, enrich=None):
    """One authentication/filter pass and one shared batch of related records.

    Each column still has its own SQL-limited page. Never fetch the complete
    organization into memory, and never derive totals from the visible cards.
    """
    params = request.query_params
    stages = stages_for(request.profile.org, queryset.model.__name__)
    selected = params.get("stage")
    stages = [s for s in stages if not selected or s["key"] == selected]
    limit = max(1, bounded_int(params.get("limit"), 25, 100))
    # Strip annotations/joins only AFTER retaining the authorized, filtered IDs.
    scoped = queryset.model.objects.filter(pk__in=queryset.order_by().values("pk"))
    counts = dict(scoped.order_by().values("stage").annotate(n=Count("pk")).values_list("stage", "n"))
    columns = []
    ids = []
    for stage in stages:
        key = stage["key"]
        offset = bounded_int(params.get(f"{key}_offset"), 0, 10000000)
        count = counts.get(key, 0)
        page_ids = list(queryset.filter(stage=key).distinct().values_list("pk", flat=True)[offset:offset + limit]) if count > offset else []
        ids.extend(page_ids)
        columns.append({
            "key": key, "count": count, "offset": offset,
            "money_totals": totals(scoped.filter(stage=key)) if count else [],
            "ids": page_ids,
        })
    records = list(queryset.filter(pk__in=ids).distinct()) if ids else []
    rows = list(serializer_class(records, many=True, context=context or {}).data)
    if enrich:
        enrich(rows)
    by_id = {str(row["id"]): row for row in rows}
    for column in columns:
        column["results"] = [by_id[str(pk)] for pk in column.pop("ids")]
    return columns
