from types import SimpleNamespace

import pytest
from django.db import IntegrityError, transaction

from accounts.models import Account
from accounts.serializer import AccountCreateSerializer
from common.api_exceptions import exception_handler
from common.record_identity import company_domain
from contacts.models import Contact
from contacts.serializer import CreateContactSerializer


@pytest.mark.parametrize(
    "value,expected",
    [
        ("https://WWW.Example.COM:443/path?ref=1#top", "example.com"),
        ("example.com?ref=1", "example.com"),
        ("https://sales.example.com", "sales.example.com"),
        ("https://www.bücher.de.", "xn--bcher-kva.de"),
        ("", ""),
        (None, ""),
        ("http://[", ""),
    ],
)
def test_domain_key(value, expected):
    assert company_domain(value) == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "model,serializer,base,duplicate,key",
    [
        (
            Contact,
            CreateContactSerializer,
            {"first_name": "One", "phone": "+13055550199"},
            {"first_name": "Two", "phone": "(305) 555-0199"},
            "phone",
        ),
        (
            Contact,
            CreateContactSerializer,
            {"first_name": "One", "email": "one@example.com"},
            {"first_name": "Two", "email": "ONE@example.com"},
            "email",
        ),
        (
            Account,
            AccountCreateSerializer,
            {"name": "One", "website": "https://www.example.com/about"},
            {"name": "Two", "website": "http://example.com/?ref=2"},
            "website",
        ),
    ],
)
def test_create_edit_and_tenant_scoped_identity(
    org_a, org_b, admin_profile, model, serializer, base, duplicate, key
):
    base = dict(base)
    duplicate = dict(duplicate)
    if model is Contact:
        base.setdefault("email", "base@example.com")
        base.setdefault("phone", "+13055550188")
        duplicate.setdefault("email", "other@example.com")
        duplicate.setdefault("phone", "+13055550177")
    request = SimpleNamespace(profile=admin_profile)
    other = model.objects.create(org=org_b, **base)
    validation = serializer(data=duplicate, request_obj=request)
    assert validation.is_valid(), validation.errors
    own = model.objects.create(org=org_a, **base)
    validation = serializer(data=duplicate, request_obj=request)
    assert not validation.is_valid()
    assert key in validation.errors
    validation = serializer(own, data=duplicate, partial=True, request_obj=request)
    assert validation.is_valid(), validation.errors
    second = model.objects.create(
        org=org_a,
        **({"first_name": "Second"} if model is Contact else {"name": "Second"}),
    )
    validation = serializer(
        second, data={key: duplicate[key]}, partial=True, request_obj=request
    )
    assert not validation.is_valid()
    assert key in validation.errors
    # Bypassing a serializer cannot race past the database rule.
    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.create(org=org_a, **duplicate)
    other.refresh_from_db()
    assert other.org_id == org_b.pk


@pytest.mark.django_db
def test_domain_edit_and_same_name_allowed(org_a):
    one = Account.objects.create(
        org=org_a, name="Same", website="https://one.example.com"
    )
    Account.objects.create(org=org_a, name="Same", website="https://two.example.com")
    Account.objects.create(org=org_a, name="Same")
    Account.objects.create(org=org_a, name="Same", website="")
    one.website = "https://www.new.example.com/path"
    one.save(update_fields=["website"])
    one.refresh_from_db()
    assert one.domain_match_key == "new.example.com"
    Account.objects.create(
        org=org_a, name="Reuse released domain", website="http://one.example.com"
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "model,values",
    [
        (Contact, {"first_name": "One", "phone": "+13055550199"}),
        (Account, {"name": "One", "website": "https://example.com"}),
    ],
)
def test_archived_merge_source_does_not_block_identity(org_a, model, values):
    from django.utils import timezone

    model.objects.create(org=org_a, merged_at=timezone.now(), **values)
    model.objects.create(org=org_a, **values)


@pytest.mark.parametrize(
    "constraint,field",
    [
        ("unique_contact_phone_per_org", "phone"),
        ("unique_account_domain_per_org", "website"),
        ("unique_contact_email_per_org", "email"),
    ],
)
def test_race_returns_field_error_without_database_details(constraint, field):
    error = IntegrityError("sensitive SQL details")
    cause = Exception()
    cause.diag = SimpleNamespace(constraint_name=constraint)
    error.__cause__ = cause
    response = exception_handler(error, {})
    assert response.status_code == 400
    assert field in response.data["errors"]
    assert "sensitive" not in str(response.data)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "target,model,serializer,values,required",
    [
        (
            "Contact",
            Contact,
            CreateContactSerializer,
            {
                "first_name": "Valid",
                "email": "valid@example.com",
                "phone": "+13055550199",
            },
            ["email", "phone"],
        ),
        (
            "Account",
            Account,
            AccountCreateSerializer,
            {"name": "Valid", "website": "example.com"},
            ["website"],
        ),
    ],
)
def test_default_required_identity_cannot_be_empty(
    org_a, admin_profile, target, model, serializer, values, required
):
    from rest_framework.exceptions import ValidationError

    from common.creation_forms import (
        configuration,
        validate_configuration,
        validate_creation,
    )

    request = SimpleNamespace(profile=admin_profile)
    for key in required:
        missing = {k: v for k, v in values.items() if k != key}
        validation = serializer(data=missing, request_obj=request)
        assert not validation.is_valid()
        assert key in validation.errors
        with pytest.raises(ValidationError):
            validate_creation(org_a, target, missing)
    config = configuration(org_a, target)
    for key in required:
        field = next(f for f in config["selected"] if f["key"] == key)
        assert field["required"]
        assert field["locked"] is (target == "Account")
        selected = [
            {"key": f["key"], "required": f["required"]}
            for f in config["selected"]
            if f["key"] != key
        ]
        if target == "Account":
            with pytest.raises(ValidationError):
                validate_configuration(org_a, target, selected)
        else:
            assert validate_configuration(org_a, target, selected) == selected
    record = model.objects.create(org=org_a, **values)
    for key in required:
        for empty in ("", None):
            validation = serializer(
                record, data={key: empty}, partial=True, request_obj=request
            )
            assert not validation.is_valid()
            assert key in validation.errors
    # Existing records are retained and can receive unrelated partial edits.
    legacy = model.objects.create(
        org=org_a,
        **({"first_name": "Legacy"} if model is Contact else {"name": "Legacy"}),
    )
    validation = serializer(
        legacy, data={"description": "Updated note"}, partial=True, request_obj=request
    )
    assert validation.is_valid(), validation.errors


@pytest.mark.django_db
def test_bare_domain_accepted_and_normalized(admin_profile):
    serializer = AccountCreateSerializer(
        data={"name": "Company", "website": "www.example.com"},
        request_obj=SimpleNamespace(profile=admin_profile),
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["website"] == "https://www.example.com"
