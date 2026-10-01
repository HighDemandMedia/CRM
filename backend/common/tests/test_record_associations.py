import pytest

from accounts.models import Account
from common.testing import rls_org
from contacts.models import Contact
from opportunity.models import Opportunity

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "kind,target_kind",
    [
        ("company", "contact"),
        ("company", "deal"),
        ("deal", "contact"),
        ("deal", "company"),
    ],
)
def test_associations(admin_client, org_a, org_b, kind, target_kind):
    models = {"company": Account, "contact": Contact, "deal": Opportunity}
    parent = models[kind].objects.create(name="Parent", org=org_a)
    fields = (
        {"first_name": "Target"} if target_kind == "contact" else {"name": "Target"}
    )
    target = models[target_kind].objects.create(org=org_a, **fields)
    with rls_org(org_b):
        foreign = models[target_kind].objects.create(org=org_b, **fields)
    url = f"/api/record-associations/{kind}/{parent.pk}/"
    choices = admin_client.get(url, {"kind": target_kind})
    assert choices.status_code == 200, choices.data
    assert len(choices.data["results"]) == 1
    body = {"kind": target_kind, "target": str(target.pk), "operation": "add"}
    assert (
        admin_client.post(
            url, {**body, "target": str(foreign.pk)}, format="json"
        ).status_code
        == 404
    )
    for operation in ["add", "remove"]:
        response = admin_client.post(
            url, {**body, "operation": operation}, format="json"
        )
        assert response.status_code == 200, response.data
        parent.refresh_from_db()
        target.refresh_from_db()
        if target_kind == "contact":
            assert parent.contacts.filter(pk=target.pk).exists() == (operation == "add")
        else:
            deal = parent if kind == "deal" else target
            company = target if kind == "deal" else parent
            assert (deal.account_id == company.pk) == (operation == "add")
    assert models[target_kind].objects.filter(pk=target.pk).exists()


def test_deal_company_not_silently_replaced(admin_client, org_a):
    first = Account.objects.create(name="First", org=org_a)
    second = Account.objects.create(name="Second", org=org_a)
    deal = Opportunity.objects.create(name="Deal", org=org_a, account=first)
    response = admin_client.post(
        f"/api/record-associations/deal/{deal.pk}/",
        {"kind": "company", "target": str(second.pk), "operation": "add"},
        format="json",
    )
    assert response.status_code == 400
    deal.refresh_from_db()
    assert deal.account_id == first.pk
