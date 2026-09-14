import pytest
from contacts.models import Contact
from accounts.models import Account
from opportunity.models import Opportunity

pytestmark=pytest.mark.django_db

@pytest.mark.parametrize('kind,model',[('company',Account),('deal',Opportunity)])
def test_add_remove_preserves_other_contacts_and_record(admin_client,org_a,org_b,kind,model):
    contact=Contact.objects.create(first_name='Contact',org=org_a)
    other=Contact.objects.create(first_name='Other',org=org_a)
    target=model.objects.create(name='Related',org=org_a)
    target.contacts.add(other)
    foreign=model.objects.create(name='Foreign',org=org_b)
    url=f'/api/contacts/{contact.pk}/associations/'
    assert admin_client.get(url,{'kind':kind}).data['results'][0]['id']==target.pk
    assert admin_client.post(url,{'kind':kind,'target':str(foreign.pk),'operation':'add'},format='json').status_code==404
    for operation in ['add','add','remove','remove']:
        response=admin_client.post(url,{'kind':kind,'target':str(target.pk),'operation':operation},format='json')
        assert response.status_code==200,response.data
        assert target.contacts.filter(pk=contact.pk).exists()==(operation=='add')
        assert target.contacts.filter(pk=other.pk).exists()
    assert model.objects.filter(pk=target.pk).exists()


def test_remove_primary_company_and_scope(admin_client,org_a,org_b,org_b_client):
    company=Account.objects.create(name='Primary',org=org_a)
    contact=Contact.objects.create(first_name='Primary contact',org=org_a,account=company)
    company.contacts.add(contact)
    url=f'/api/contacts/{contact.pk}/associations/'
    assert org_b_client.get(url,{'kind':'company'}).status_code==404
    response=admin_client.post(url,{'kind':'company','target':str(company.pk),'operation':'remove'},format='json')
    assert response.status_code==200,response.data
    contact.refresh_from_db()
    assert contact.account_id is None
    assert not company.contacts.filter(pk=contact.pk).exists()
