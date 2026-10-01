from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import Account
from accounts.views import annotate_rollups
from opportunity.models import Opportunity

pytestmark = pytest.mark.django_db


def test_past_due_deals_counts_open_deals_before_today(org_a):
    company = Account.objects.create(name="Dates", org=org_a)
    other = Account.objects.create(name="Other dates", org=org_a)
    today = timezone.localdate()
    for stage, date, account in [
        ("PROSPECTING", today - timedelta(days=1), company),
        ("QUALIFICATION", today - timedelta(days=3), company),
        ("PROPOSAL", today, company),
        ("PROSPECTING", today + timedelta(days=1), company),
        ("PROSPECTING", None, company),
        ("CLOSED_WON", today - timedelta(days=1), company),
        ("CLOSED_LOST", today - timedelta(days=1), company),
        ("PROSPECTING", today - timedelta(days=1), other),
    ]:
        Opportunity.objects.create(
            name="Date test", org=org_a, account=account, stage=stage, closed_on=date
        )

    def count():
        return (
            annotate_rollups(Account.objects.filter(pk=company.pk))
            .get()
            .overdue_deal_count
        )

    assert count() == 2
    Opportunity.objects.filter(account=company, stage="QUALIFICATION").update(
        closed_on=today
    )
    assert count() == 1
    Opportunity.objects.filter(account=company, closed_on__lt=today).update(
        stage="CLOSED_WON"
    )
    assert count() == 0
