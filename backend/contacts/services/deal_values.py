"""Batch deal totals for the contacts visible on a pipeline page."""

from django.db.models import Q, Sum

from common.permissions import is_org_admin
from opportunity.models import Opportunity


def contact_deal_values(profile, user, contact_ids):
    if not contact_ids:
        return {}
    deals = Opportunity.objects.filter(org=profile.org)
    if not (is_org_admin(profile) or user.is_superuser):
        visible_ids = deals.filter(
            Q(created_by=profile.user) | Q(assigned_to=profile)
        ).values("pk")
        deals = deals.filter(pk__in=visible_ids)
    totals = (
        deals.filter(contacts__id__in=contact_ids)
        .order_by()
        .values("contacts__id", "currency")
        .annotate(total=Sum("amount"))
        .order_by("currency")
    )
    result = {}
    for row in totals:
        result.setdefault(str(row["contacts__id"]), []).append(
            {
                "currency": row["currency"] or "",
                "amount": str(row["total"]) if row["total"] is not None else None,
            }
        )
    return result


def contact_pipeline_totals(profile, user, contact_ids):
    """Count each visible associated deal once, even across several contacts."""
    from common.money_totals import money_totals

    deals = Opportunity.objects.filter(org=profile.org, contacts__id__in=contact_ids)
    if not (is_org_admin(profile) or user.is_superuser):
        deals = deals.filter(Q(created_by=profile.user) | Q(assigned_to=profile))
    return money_totals(deals)
