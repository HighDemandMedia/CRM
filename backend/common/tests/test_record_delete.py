import pytest
from accounts.models import Account
from contacts.models import Contact
from opportunity.models import Opportunity

pytestmark=pytest.mark.django_db

@pytest.mark.parametrize('kind,model',[('contact',Contact),('company',Account),('deal',Opportunity)])
def test_confirmed_delete(admin_client,org_a,org_b_client,kind,model):
    fields={'first_name':'Delete me'} if kind=='contact' else {'name':'Delete me'}
    record=model.objects.create(org=org_a,**fields)
    url=f'/api/record-delete/{kind}/{record.pk}/'
    assert org_b_client.get(url).status_code==404
    preview=admin_client.get(url)
    assert preview.status_code==200,preview.data
    assert not preview.data['blocked']
    assert admin_client.post(url,{'confirmation':record.name},format='json').status_code==400
    assert admin_client.post(url,{'confirmation':'wrong','token':preview.data['token']},format='json').status_code==400
    assert model.objects.filter(pk=record.pk).exists()
    response=admin_client.post(url,{'confirmation':record.name,'token':preview.data['token']},format='json')
    assert response.status_code==200,response.data
    assert not model.objects.filter(pk=record.pk).exists()


def test_changed_impact_requires_new_preview(admin_client,org_a,user_client):
    company=Account.objects.create(name='Company',org=org_a)
    url=f'/api/record-delete/company/{company.pk}/'
    assert user_client.get(url).status_code==403
    preview=admin_client.get(url).data
    deal=Opportunity.objects.create(name='New linked deal',account=company,org=org_a)
    response=admin_client.post(url,{'confirmation':company.name,'token':preview['token']},format='json')
    assert response.status_code==409,response.data
    assert Opportunity.objects.filter(pk=deal.pk).exists()
    preview=admin_client.get(url).data
    assert {'label':'Deals','count':1} not in preview['counts']
    assert preview['associated'] == [{'kind':'deal','name':'New linked deal'}]


@pytest.mark.parametrize('kind', ['company', 'contact', 'deal'])
@pytest.mark.parametrize('include', [False, True])
def test_keep_or_delete_direct_associations(admin_client, org_a, kind, include):
    company = Account.objects.create(name='Linked company', org=org_a)
    contact = Contact.objects.create(first_name='Linked contact', org=org_a, account=company)
    company.contacts.add(contact)
    deal = Opportunity.objects.create(name='Linked deal', org=org_a, account=company)
    deal.contacts.add(contact)
    # A second level association must survive even when its company is selected.
    extra_deal = Opportunity.objects.create(name='Other deal', org=org_a, account=company)
    records = {'company': company, 'contact': contact, 'deal': deal}
    record = records[kind]
    url = f'/api/record-delete/{kind}/{record.pk}/'
    preview = admin_client.get(url, {'include_associated': str(include).lower()}).data
    assert not preview['blocked'], preview
    response = admin_client.post(url, {'confirmation': record.name, 'token': preview['token']}, format='json')
    assert response.status_code == 200, response.data
    for key, obj in records.items():
        assert type(obj).objects.filter(pk=obj.pk).exists() == (key != kind and not include)
    if not (kind == 'company' and include):
        extra_deal.refresh_from_db()
        assert extra_deal.account_id == (company.pk if kind != 'company' and not include else None)
    if not include and kind == 'company':
        contact.refresh_from_db()
        deal.refresh_from_db()
        assert contact.account_id is None
        assert deal.account_id is None
    if not include and kind == 'contact':
        assert not company.contacts.exists()
        assert not deal.contacts.exists()


@pytest.mark.parametrize('kind', ['company', 'contact', 'deal'])
def test_billing_documents_survive_company_deletion(admin_client, org_a, kind):
    from invoices.models import Invoice, Estimate, RecurringInvoice
    company = Account.objects.create(name='Billing company', org=org_a)
    contact = Contact.objects.create(first_name='Client', account=company, org=org_a)
    deal = Opportunity.objects.create(name='Deal', account=company, org=org_a)
    documents = [
        Invoice.objects.create(org=org_a, account=company, invoice_title='Invoice', invoice_number='DELETE-TEST', client_name='Stored client'),
        Estimate.objects.create(org=org_a, account=company, title='Estimate', estimate_number='DELETE-TEST', client_name='Stored client'),
        RecurringInvoice.objects.create(org=org_a, account=company, title='Recurring', client_name='Stored client'),
    ]
    record = {'company': company, 'contact': contact, 'deal': deal}[kind]
    url = f'/api/record-delete/{kind}/{record.pk}/'
    preview = admin_client.get(url, {'include_associated': 'true'}).data
    assert not preview['blocked'], preview
    # Preview must never detach records.
    for document in documents:
        document.refresh_from_db()
        assert document.account_id == company.pk
    response = admin_client.post(url, {'token': preview['token'], 'confirmation': record.name}, format='json')
    assert response.status_code == 200, response.data
    assert not Account.objects.filter(pk=company.pk).exists()
    for document in documents:
        document.refresh_from_db()
        assert document.account_id is None
        assert document.client_name == 'Stored client'
