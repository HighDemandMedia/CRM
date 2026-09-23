import pytest

from accounts.models import Account
from contacts.models import Contact
from opportunity.models import Opportunity

pytestmark = pytest.mark.django_db


def payload(admin_profile):
    return {
        "name": "Properties deal",
        "stage": "PROSPECTING",
        "assigned_to": [str(admin_profile.pk)],
        "priority": "HIGH",
        "lead_source": "META",
        "address_line": "123 Main St",
        "city": "Miami",
        "state": "FL",
        "postcode": "33101",
        "country": "US",
    }


@pytest.mark.parametrize("association", ["contact", "company", "both"])
def test_create_deal_properties(admin_client, admin_profile, org_a, association):
    body = payload(admin_profile)
    contact = Contact.objects.create(first_name="Linked", org=org_a)
    company = Account.objects.create(name="Linked company", org=org_a)
    if association in ["contact", "both"]:
        body["contacts"] = [str(contact.pk)]
    if association in ["company", "both"]:
        body["account"] = str(company.pk)
    response = admin_client.post("/api/opportunities/", body, format="json")
    assert response.status_code == 200, response.data
    deal = Opportunity.objects.get(name=body["name"], org=org_a)
    assert deal.amount is None and deal.closed_on is None
    assert deal.priority == "HIGH" and deal.city == "Miami"
    assert deal.assigned_to.filter(pk=admin_profile.pk).exists()
    if "contacts" in body:
        assert deal.contacts.filter(pk=contact.pk).exists()
    response = admin_client.get(f"/api/opportunities/{deal.pk}/")
    assert response.data["opportunity_obj"]["priority"] == "HIGH"
    response = admin_client.patch(
        f"/api/opportunities/{deal.pk}/", {"stage": "CLOSED_WON"}, format="json"
    )
    assert response.status_code == 200, response.data


@pytest.mark.parametrize(
    "field", ["stage", "priority", "lead_source", "assigned_to"]
)
def test_optional_fields(admin_client, admin_profile, org_a, field):
    body = payload(admin_profile)
    body["account"] = str(Account.objects.create(name="Company", org=org_a).pk)
    body.pop(field)
    response = admin_client.post("/api/opportunities/", body, format="json")
    assert response.status_code == 200, response.data


def test_associations_and_owner_scope(admin_client, admin_profile, org_a, org_b):
    body = payload(admin_profile)
    assert (
        admin_client.post("/api/opportunities/", body, format="json").status_code == 200
    )
    body["name"] = "Scope validation"
    foreign = Contact.objects.create(first_name="Foreign", org=org_b)
    body["contacts"] = [str(foreign.pk)]
    assert (
        admin_client.post("/api/opportunities/", body, format="json").status_code == 400
    )
    body.pop("contacts")
    body["account"] = str(Account.objects.create(name="Foreign company", org=org_b).pk)
    assert (
        admin_client.post("/api/opportunities/", body, format="json").status_code == 400
    )
    body["account"] = str(Account.objects.create(name="Local company", org=org_a).pk)
    body["assigned_to"] = [str(foreign.pk)]
    assert (
        admin_client.post("/api/opportunities/", body, format="json").status_code == 400
    )


def test_phone_email_and_tags(admin_client, admin_profile, org_a):
    from common.models import Tags
    company = Account.objects.create(name='Company', org=org_a)
    tag = Tags.objects.create(name='Deal tag', color='blue', org=org_a)
    body = {**payload(admin_profile), 'account':str(company.pk), 'phone':'3055550188',
            'email':'deal@example.com', 'tags':[str(tag.pk)]}
    response = admin_client.post('/api/opportunities/',body,format='json')
    assert response.status_code == 200, response.data
    deal = Opportunity.objects.get(name=body['name'],org=org_a)
    assert deal.phone == body['phone'] and deal.email == body['email']
    assert deal.tags.filter(pk=tag.pk).exists()
    url = f'/api/opportunities/{deal.pk}/'
    detail = admin_client.get(url).data['opportunity_obj']
    assert detail['phone'] == body['phone'] and detail['email'] == body['email']
    assert admin_client.patch(url,{'email':'invalid'},format='json').status_code == 400
    assert admin_client.patch(url,{'name':'Renamed'},format='json').status_code == 200
    deal.refresh_from_db()
    assert deal.phone == body['phone'] and deal.tags.filter(pk=tag.pk).exists()
    response = admin_client.patch(url,{'phone':None,'email':None,'tags':[]},format='json')
    assert response.status_code == 200, response.data
    deal.refresh_from_db()
    assert deal.phone is None and deal.email is None and not deal.tags.exists()
