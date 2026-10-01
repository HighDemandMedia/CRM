"""Currency-separated totals without duplicating records joined by relations."""

from django.db.models import Sum


def money_totals(queryset, field="amount"):
    rows = queryset.model.objects.filter(pk__in=queryset.order_by().values("pk"))
    return [
        {"currency": row["currency"] or "", "amount": str(row["total"])}
        for row in rows.order_by()
        .values("currency")
        .annotate(total=Sum(field))
        .order_by("currency")
        if row["total"] is not None
    ]
