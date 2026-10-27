from types import SimpleNamespace

import pytest
from rest_framework.exceptions import ValidationError

from accounts.models import Account
from contacts.models import Contact
from leads.models import Lead
from leads.services import convert_lead_to_account

pytestmark = pytest.mark.django_db


def make_lead(org, **values):
    fields = dict(
        org=org,
        first_name="Lead",
        last_name="Example",
        company_name="Same name",
        website="https://www.example.com/path",
        email="lead@example.com",
        phone="+12025550111",
    )
    fields.update(values)
    return Lead.objects.create(**fields)


def test_conversion_matches_domain_and_phone_without_overwriting(org_a, admin_profile):
    company = Account.objects.create(
        org=org_a, name="Original name", website="https://example.com"
    )
    contact = Contact.objects.create(
        org=org_a,
        first_name="Original",
        email="original@example.com",
        phone="+12025550111",
    )
    lead = make_lead(org_a)
    account, matched, opportunity = convert_lead_to_account(
        lead, SimpleNamespace(profile=admin_profile), create_opportunity=False
    )
    assert account.pk == company.pk
    assert matched.pk == contact.pk
    assert account.contacts.filter(pk=contact.pk).exists()
    contact.refresh_from_db()
    assert contact.email == "original@example.com"
    assert contact.first_name == "Original"
    assert opportunity is None


def test_conversion_shared_company_name_does_not_merge(org_a, admin_profile):
    old = Account.objects.create(
        org=org_a, name="Same name", website="https://other.example.com"
    )
    account, contact, _ = convert_lead_to_account(
        make_lead(org_a),
        SimpleNamespace(profile=admin_profile),
        create_opportunity=False,
    )
    assert account.pk != old.pk
    assert account.domain_match_key == "example.com"
    assert contact.email == "lead@example.com"
    assert account.contacts.filter(pk=contact.pk).exists()


@pytest.mark.parametrize("missing", ["website", "email", "phone"])
def test_conversion_missing_identity_rolls_back(org_a, admin_profile, missing):
    lead = make_lead(org_a, **{missing: ""})
    with pytest.raises(ValidationError):
        convert_lead_to_account(
            lead, SimpleNamespace(profile=admin_profile), create_opportunity=False
        )
    assert not Account.objects.filter(org=org_a).exists()
    assert not Contact.objects.filter(org=org_a).exists()
    lead.refresh_from_db()
    assert lead.status != "converted"
