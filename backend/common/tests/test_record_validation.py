import pytest
from rest_framework.exceptions import ValidationError
from common.record_validation import clean_record_values


@pytest.mark.parametrize('field,value', [
    ('city', '1234'), ('city', '<Miami>'), ('city', 'https://miami.test'),
    ('state', '@@@'), ('postcode', '!!!'), ('phone', '-------'),
    ('phone', '123456'), ('phone', '1234567890123456'), ('phone', '1+3055550190'),
    ('address_line', 'Street\nOther'),
])
def test_invalid_formats(field, value):
    with pytest.raises(ValidationError) as error:
        clean_record_values({field: value}, 'Contact')
    assert field in error.value.detail


@pytest.mark.parametrize('field,value', [
    ('city', 'São Paulo'), ('city', '東京'), ('city', "St. John's"),
    ('city', 'Winston-Salem'), ('city', '6th of October City'),
    ('state', 'Île-de-France'), ('postcode', 'SW1A 1AA'), ('postcode', '00901-1234'),
    ('phone', '+1 (305) 555-0190'), ('phone', '3055550190'),
])
def test_international_formats(field, value):
    assert clean_record_values({field: value}, 'Account')[field] == value


def test_optional_and_whitespace():
    assert clean_record_values({'city': '  São   Paulo  ', 'state': '', 'phone': None}, 'Contact') == {
        'city': 'São Paulo', 'state': '', 'phone': None}


@pytest.mark.django_db
@pytest.mark.parametrize('route', ['contacts', 'accounts', 'opportunities'])
def test_api_validates_address_and_preserves_optional_fields(admin_client, route):
    bad = admin_client.post(f'/api/{route}/', {'name': 'Form QA', 'city': '1234'}, format='json')
    assert bad.status_code == 400, bad.data
    assert 'city' in str(bad.data)
    bad_email = admin_client.post(f'/api/{route}/', {'name': 'Form QA', 'email': 'invalid'}, format='json')
    assert bad_email.status_code == 400, bad_email.data
    good = admin_client.post(f'/api/{route}/', {'name': 'Form QA', 'city': '  São   Paulo ',
        'postcode': '01310-100', 'country': 'BR', 'phone': '', 'email': ''}, format='json')
    assert good.status_code in (200, 201), good.data


@pytest.mark.django_db
@pytest.mark.parametrize('phone,valid', [('', True), ('+1 (305) 555-0190', True), ('-------', False)])
def test_lead_serializer_uses_same_phone_rules(admin_profile, phone, valid):
    from types import SimpleNamespace
    from leads.serializer import LeadCreateSerializer
    serializer = LeadCreateSerializer(data={'first_name': 'Lead QA', 'phone': phone},
        request_obj=SimpleNamespace(profile=admin_profile))
    assert serializer.is_valid() is valid, serializer.errors
    if not valid:
        assert 'phone' in serializer.errors
