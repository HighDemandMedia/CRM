"""Regressions found in the production TESTING acceptance run."""

from types import SimpleNamespace

import pytest
from django.utils import timezone

from accounts.models import Account
from cases.models import Case
from common.models import CRMRole
from common.rbac import default_rules
from opportunity.models import Opportunity
from opportunity.serializer import OpportunityCreateSerializer
from tasks.models import Task

pytestmark = pytest.mark.django_db


def test_task_owner_choices_include_saved_name(admin_client, admin_user):
    admin_user.name = "QA Administrator"
    admin_user.save(update_fields=["name"])
    people = admin_client.get("/api/tasks/?limit=1").data["users"]
    person = next(p for p in people if p["user__email"] == admin_user.email)
    assert person["user__name"] == "QA Administrator"


@pytest.mark.parametrize(
    "field,model,values",
    [
        ("account", Account, {"name": "Restricted company"}),
        ("opportunity", Opportunity, {"name": "Restricted deal"}),
        ("case", Case, {"name": "Restricted ticket"}),
    ],
)
def test_task_does_not_disclose_inaccessible_parent(
    user_client, user_profile, org_a, field, model, values
):
    role = CRMRole.objects.create(
        org=org_a, name="Own records", rules=default_rules("own")
    )
    user_profile.access_role = role
    user_profile.save(update_fields=["access_role"])
    parent = model.objects.create(org=org_a, **values)
    task = Task.objects.create(org=org_a, title="Visible task", **{field: parent})
    task.assigned_to.add(user_profile)
    listing = user_client.get("/api/tasks/")
    assert listing.status_code == 200
    row = next(row for row in listing.data["tasks"] if row["id"] == str(task.pk))
    assert row[field] is None
    detail = user_client.get(f"/api/tasks/{task.pk}/")
    assert detail.status_code == 200
    assert detail.data["task_obj"][field] is None
    parent.assigned_to.add(user_profile)
    visible = user_client.get(f"/api/tasks/{task.pk}/")
    assert visible.data["task_obj"][field] == {
        "id": str(parent.pk),
        "name": values["name"],
    }


@pytest.mark.parametrize("currency", [None, "", "GBP"])
def test_deal_creation_defaults_currency_from_request_org(
    org_a, admin_profile, currency
):
    org_a.default_currency = "EUR"
    org_a.save(update_fields=["default_currency"])
    admin_profile.org = org_a
    data = {"name": "Currency QA", "amount": "12000"}
    if currency is not None:
        data["currency"] = currency
    serializer = OpportunityCreateSerializer(
        data=data, request_obj=SimpleNamespace(profile=admin_profile)
    )
    assert serializer.is_valid(), serializer.errors
    deal = serializer.save(org=org_a)
    assert deal.currency == (currency or "EUR")


def test_member_count_excludes_support_and_removed_profiles(
    admin_client, user_profile, admin_profile
):
    assert admin_client.get("/api/org/settings/").data["member_count"] == 2
    user_profile.is_platform_access = True
    user_profile.save(update_fields=["is_platform_access"])
    assert admin_client.get("/api/org/settings/").data["member_count"] == 1
    user_profile.is_platform_access = False
    user_profile.removed_at = timezone.now()
    user_profile.save(update_fields=["is_platform_access", "removed_at"])
    assert admin_client.get("/api/org/settings/").data["member_count"] == 1
