import pytest
from accounts.models import Account
from contacts.models import Contact
from cases.models import Case

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("operation", ["add", "remove"])
def test_contact_cannot_change_ticket_associations(admin_client, admin_user, org_a, operation):
    contact = Contact.objects.create(first_name="Associate", org=org_a, created_by=admin_user)
    ticket = Case.objects.create(name="Association test", org=org_a, created_by=admin_user)
    if operation == "remove":
        ticket.contacts.add(contact)
    url = f"/api/contacts/{contact.pk}/associations/"
    response = admin_client.post(url, {
        "kind": "ticket", "target": str(ticket.pk), "operation": operation
    }, format="json")
    assert response.status_code == 400
    assert ticket.contacts.filter(pk=contact.pk).exists() == (operation == "remove")
    assert admin_client.get(url, {"kind": "ticket"}).status_code == 400
    assert Case.objects.filter(pk=ticket.pk).exists()


@pytest.mark.parametrize("operation", ["add", "remove"])
def test_company_cannot_change_ticket_associations(admin_client, admin_user, org_a, operation):
    company = Account.objects.create(name="Associated company", org=org_a, created_by=admin_user)
    account = company if operation == "remove" else None
    ticket = Case.objects.create(name="Association test", account=account, org=org_a, created_by=admin_user)
    url = f"/api/record-associations/company/{company.pk}/"
    response = admin_client.post(url, {
        "kind": "ticket", "target": str(ticket.pk), "operation": operation
    }, format="json")
    assert response.status_code == 400
    ticket.refresh_from_db()
    assert ticket.account_id == (company.pk if operation == "remove" else None)
    assert admin_client.get(url, {"kind": "ticket"}).status_code == 400
