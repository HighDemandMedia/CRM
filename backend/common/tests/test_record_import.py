from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from common.models import CSVImportReceipt, CustomFieldDefinition
from common.property_catalog import target_model
from common.record_import import COMMIT_BATCH_SIZE, MAX_ROWS
from common.tests.csv_fixtures import with_identities

pytestmark = pytest.mark.django_db
OBJECTS = [
    ("contacts", "Contact", "first_name"),
    ("companies", "Account", "name"),
    ("deals", "Opportunity", "name"),
    ("tasks", "Task", "title"),
    ("tickets", "Case", "name"),
]


@pytest.mark.parametrize("module,target,key", OBJECTS)
def test_compact_ids_preserve_import_associations(
    admin_client, admin_profile, org_a, org_b, module, target, key
):
    from accounts.models import Account
    from common.models import BusinessIDSequence
    from common.rls.context import org_context
    from contacts.models import Contact

    company = Account.objects.create(org=org_a, name="Shared company name")
    contacts = [
        Contact.objects.create(
            org=org_a, first_name=f"Existing {i}", email=f"existing{i}@example.com"
        )
        for i in range(2)
    ]
    # Identical lookup values in a different tenant must never win the match.
    with org_context(org_b.pk):
        Account.objects.create(org=org_b, name=company.name)
        Contact.objects.create(org=org_b, first_name="Foreign", email=contacts[0].email)
    model = target_model(target)
    prefix = model._meta.pk.prefix
    BusinessIDSequence.objects.update_or_create(
        pk=prefix, defaults={"last_number": 9999}
    )
    headers = [key, "assigned_to"]
    values = ["Imported association", admin_profile.user.email]
    if module != "companies":
        headers.append("account")
        values.append(company.name)
    if module != "contacts":
        headers.append("contacts")
        values.append(";".join(contact.email for contact in contacts))
    content = ",".join(headers) + "\n" + ",".join(values) + "\n"

    preview = upload(admin_client, module, content)
    assert preview.status_code == 200, preview.data
    assert preview.data["errors"] == [], preview.data
    assert BusinessIDSequence.objects.get(pk=prefix).last_number == 9999
    result = upload(
        admin_client, module, content, action="commit", token=preview.data["token"]
    )
    assert result.status_code == 200, result.data
    record = model.objects.get(pk=f"{prefix}-10000", org=org_a)
    assert list(record.assigned_to.all()) == [admin_profile]
    if module != "companies":
        assert record.account_id == company.pk
    if module != "contacts":
        assert set(record.contacts.values_list("pk", flat=True)) == {
            contact.pk for contact in contacts
        }
    else:
        assert company.contacts.filter(pk=record.pk).exists()
    retry = upload(
        admin_client, module, content, action="commit", token=preview.data["token"]
    )
    assert retry.data["already_imported"] is True
    assert BusinessIDSequence.objects.get(pk=prefix).last_number == 10000


@pytest.mark.parametrize("module,target,key", OBJECTS)
def test_csv_cannot_supply_or_replace_primary_keys(admin_client, module, target, key):
    prefix = target_model(target)._meta.pk.prefix
    response = upload(admin_client, module, f"{key},id\nSpoofed,{prefix}-0001\n")
    assert response.status_code == 400, response.data


def upload(client, module, content, *, complete_identity=True, **extra):
    if complete_identity:
        content = with_identities(module, content)
    return client.post(
        f"/api/record-import/{module}/",
        {
            "file": SimpleUploadedFile(
                "records.csv", content.encode("utf-8"), content_type="text/csv"
            ),
            **extra,
        },
        format="multipart",
    )


@pytest.fixture(autouse=True)
def no_assignment_email():
    with (
        patch("contacts.views.send_email_to_assigned_user.delay_on_commit"),
        patch("accounts.views.send_email_to_assigned_user.delay_on_commit"),
        patch("cases.views.send_email_to_assigned_user.delay_on_commit"),
        patch(
            "opportunity.views.opportunity_views.send_email_to_assigned_user.delay_on_commit"
        ),
    ):
        yield


@pytest.mark.parametrize("module,target,key", OBJECTS)
def test_preview_commit_and_idempotent_retry(
    admin_client, admin_profile, org_a, module, target, key
):
    content = f"{key},assigned_to\nCSV test,{admin_profile.user.email}\n"
    before = target_model(target).objects.filter(org=org_a).count()
    preview = upload(admin_client, module, content)
    assert preview.status_code == 200, preview.data
    assert preview.data["errors"] == [], preview.data
    assert preview.data["token"]
    assert target_model(target).objects.filter(org=org_a).count() == before
    commit = upload(
        admin_client, module, content, action="commit", token=preview.data["token"]
    )
    assert commit.status_code == 200, commit.data
    assert commit.data["created"] == 1
    record = target_model(target).objects.filter(org=org_a).latest("created_at")
    assert list(record.assigned_to.all()) == [admin_profile]
    again = upload(
        admin_client, module, content, action="commit", token=preview.data["token"]
    )
    assert again.status_code == 200, again.data
    assert again.data["already_imported"] is True
    assert target_model(target).objects.filter(org=org_a).count() == before + 1
    assert CSVImportReceipt.objects.filter(org=org_a).count() == 1


@pytest.mark.parametrize("module,target,key", OBJECTS)
def test_member_cannot_preview_or_commit(user_client, module, target, key):
    assert user_client.get(f"/api/record-import/{module}/").status_code == 403
    assert upload(user_client, module, f"{key}\nTest\n").status_code == 403
    assert (
        upload(
            user_client, module, f"{key}\nTest\n", action="commit", token="fake"
        ).status_code
        == 403
    )


def test_custom_fields_and_required_configuration(admin_client, org_a):
    CustomFieldDefinition.objects.create(
        org=org_a,
        target_model="Contact",
        key="reference",
        label="Reference",
        field_type="text",
    )
    org_a.creation_forms = {
        "Contact": [
            {"key": "first_name", "required": True},
            {"key": "custom_fields.reference", "required": True},
        ]
    }
    org_a.save()
    meta = admin_client.get("/api/record-import/contacts/").data
    assert any(
        f["key"] == "custom_fields.reference" and f["required"] for f in meta["fields"]
    )
    response = upload(admin_client, "contacts", "first_name\nNo reference\n")
    assert response.data["token"] is None
    assert response.data["errors"][0]["field"] == "custom_fields.reference"
    valid = "first_name,custom_fields.reference\nCustom test,ABC\n"
    preview = upload(admin_client, "contacts", valid)
    assert preview.data["errors"] == []
    commit = upload(
        admin_client, "contacts", valid, action="commit", token=preview.data["token"]
    )
    assert commit.status_code == 200, commit.data
    assert target_model("Contact").objects.get(
        org=org_a, first_name="Custom test"
    ).custom_fields == {"reference": "ABC"}


def test_invalid_phone_email_and_file_errors(admin_client):
    result = upload(
        admin_client, "contacts", "first_name,email,phone\nTest,not-email,abc\n"
    )
    assert result.data["errors"] and not result.data["token"]
    for content in [
        "first_name,unknown\nTest,X\n",
        "first_name,first_name\nA,B\n",
        "first_name\n",
        "first_name,email\nOne,a@example.com,extra\n",
        "first_name\n" + "Test\n" * (MAX_ROWS + 1),
    ]:
        assert upload(admin_client, "contacts", content).status_code == 400


def test_references_cannot_cross_tenants(admin_client, profile_b):
    result = upload(
        admin_client,
        "contacts",
        f"first_name,assigned_to\nTest,{profile_b.user.email}\n",
    )
    assert result.data["errors"][0]["field"] == "assigned_to"
    assert not result.data["token"]


def test_duplicate_email_excludes_only_the_repeated_row(admin_client, org_a):
    content = "first_name,email\nOne,same@example.com\nTwo,SAME@example.com\n"
    result = upload(admin_client, "contacts", content)
    assert result.data["token"] and result.data["errors"][0]["row"] == 3
    assert result.data["valid"] == 1
    assert result.data["invalid_records"][0]["row"] == 3
    assert target_model("Contact").objects.filter(org=org_a).count() == 0


def test_preview_file_token_tenant_and_revision_binding(
    admin_client, org_b_client, org_a
):
    content = "first_name\nToken test\n"
    result = upload(admin_client, "contacts", content)
    token = result.data["token"]
    assert (
        upload(
            admin_client,
            "contacts",
            "first_name\nChanged\n",
            action="commit",
            token=token,
        ).status_code
        == 400
    )
    assert (
        upload(
            org_b_client, "contacts", content, action="commit", token=token
        ).status_code
        == 400
    )
    org_a.creation_forms = {
        "Contact": [
            {"key": "first_name", "required": True},
            {"key": "email", "required": True},
        ]
    }
    org_a.save()
    assert (
        upload(
            admin_client, "contacts", content, action="commit", token=token
        ).status_code
        == 400
    )


def test_quota_rechecked_after_preview(admin_client, org_a):
    content = "first_name\nQuota test\n"
    result = upload(admin_client, "contacts", content)
    org_a.usage_limits = {"contacts": 0}
    org_a.save()
    response = upload(
        admin_client, "contacts", content, action="commit", token=result.data["token"]
    )
    assert response.status_code == 400, response.data
    assert target_model("Contact").objects.filter(org=org_a).count() == 0
    assert not CSVImportReceipt.objects.exists()


def test_atomic_rollback_when_later_create_fails(admin_client, org_a):
    from rest_framework.response import Response

    from accounts.views import AccountsListView

    content = "name\nFirst company\nSecond company\n"
    result = upload(admin_client, "companies", content)
    assert result.data["token"], result.data
    original = AccountsListView.post

    def fail_second(view, request):
        if request.data["name"] == "Second company":
            return Response({"errors": {"name": "Concurrent conflict"}}, status=400)
        return original(view, request)

    with patch.object(AccountsListView, "post", fail_second):
        response = upload(
            admin_client,
            "companies",
            content,
            action="commit",
            token=result.data["token"],
        )
    assert response.status_code == 400, response.data
    assert not target_model("Account").objects.filter(org=org_a).exists()
    assert not CSVImportReceipt.objects.exists()


def test_utf8_bom_semicolon_and_quoted_multiline(admin_client, org_a):
    content = '\ufefffirst_name;description\nJosé;"Line one\nLine two"\n'
    result = upload(admin_client, "contacts", content)
    assert result.status_code == 200, result.data
    assert not result.data["errors"]
    assert "preview" not in result.data
    response = upload(
        admin_client, "contacts", content, action="commit", token=result.data["token"]
    )
    assert response.status_code == 200
    assert (
        target_model("Contact").objects.get(org=org_a, first_name="José").description
        == "Line one\nLine two"
    )


@pytest.mark.parametrize("module", ["deals"])
def test_duplicate_names_in_batch_rejected_at_preview(admin_client, module):
    result = upload(admin_client, module, "name\nSame\nsame\n")
    assert result.data["token"]
    assert result.data["valid"] == 1
    assert result.data["errors"][0]["row"] == 3


def test_closed_organization_cannot_import(admin_client, org_a):
    from django.utils import timezone

    org_a.closing_at = timezone.now()
    org_a.save()
    assert upload(admin_client, "contacts", "first_name\nBlocked\n").status_code == 403


def test_associations_and_existing_tags(admin_client, org_a, admin_profile):
    from accounts.models import Account
    from common.models import Tags
    from contacts.models import Contact

    company = Account.objects.create(org=org_a, name="CSV Company")
    contact = Contact.objects.create(
        org=org_a, first_name="Existing", email="existing@example.com"
    )
    tag = Tags.objects.create(org=org_a, name="Existing tag")
    content = f"name,contacts,tags,assigned_to\nCSV Other Company,existing@example.com,Existing tag,{admin_profile.user.email}\n"
    preview = upload(admin_client, "companies", content)
    assert preview.data["errors"] == [], preview.data
    result = upload(
        admin_client, "companies", content, action="commit", token=preview.data["token"]
    )
    assert result.status_code == 200, result.data
    record = Account.objects.get(org=org_a, name="CSV Other Company")
    assert list(record.contacts.all()) == [contact]
    assert list(record.tags.all()) == [tag]
    task = f"title,assigned_to,account,contacts\nCSV task,{admin_profile.user.email},{company.name},existing@example.com\n"
    preview = upload(admin_client, "tasks", task)
    assert preview.data["errors"] == [], preview.data
    result = upload(
        admin_client, "tasks", task, action="commit", token=preview.data["token"]
    )
    assert result.status_code == 200, result.data
    record = target_model("Task").objects.get(org=org_a, title="CSV task")
    assert record.account == company
    assert list(record.contacts.all()) == [contact]


def test_full_batch_limit(admin_client, org_a):
    content = "first_name\n" + "\n".join(f"CSV Person {i}" for i in range(MAX_ROWS))
    preview = upload(admin_client, "contacts", content)
    assert preview.data["valid"] == MAX_ROWS, preview.data
    completed = 0
    while completed < MAX_ROWS:
        result = upload(
            admin_client,
            "contacts",
            content,
            action="commit",
            token=preview.data["token"],
            start=completed,
        )
        assert result.status_code == 200, result.data
        assert result.data["created"] == min(completed + COMMIT_BATCH_SIZE, MAX_ROWS)
        completed = result.data["created"]
    assert result.data["complete"]
    assert target_model("Contact").objects.filter(org=org_a).count() == MAX_ROWS


def test_deal_uses_organization_currency(admin_client, org_a):
    org_a.default_currency = "EUR"
    org_a.save()
    content = "name,amount\nCSV Euro deal,10\n"
    preview = upload(admin_client, "deals", content)
    result = upload(
        admin_client, "deals", content, action="commit", token=preview.data["token"]
    )
    assert result.status_code == 200, result.data
    assert (
        target_model("Opportunity")
        .objects.get(org=org_a, name="CSV Euro deal")
        .currency
        == "EUR"
    )


@pytest.mark.parametrize("module,target,key", OBJECTS)
def test_mixed_file_imports_only_valid_rows(
    admin_client, admin_profile, org_a, module, target, key
):
    content = f"{key},assigned_to\nValid,{admin_profile.user.email}\nInvalid,not-a-user@example.com\n"
    preview = upload(admin_client, module, content)
    assert preview.status_code == 200, preview.data
    assert (preview.data["total"], preview.data["valid"], preview.data["invalid"]) == (
        2,
        1,
        1,
    )
    assert len(preview.data["invalid_records"]) == 1
    result = upload(
        admin_client, module, content, action="commit", token=preview.data["token"]
    )
    assert result.status_code == 200, result.data
    assert result.data["created"] == 1 and result.data["skipped"] == 1
    assert target_model(target).objects.filter(org=org_a).count() == 1


def test_thousand_rows_with_eight_hundred_errors_and_retry(admin_client, org_a):
    content = "first_name,email\n" + "\n".join(
        f"Person {i}," + (f"person{i}@example.com" if i < 200 else "bad-email")
        for i in range(1000)
    )
    org_a.usage_limits = {"contacts": 200}
    org_a.save()
    preview = upload(admin_client, "contacts", content)
    assert preview.status_code == 200, preview.data
    assert preview.data["valid"] == 200
    assert preview.data["invalid"] == 800
    assert len(preview.data["invalid_records"]) == 800
    assert preview.data["invalid_records"][-1]["row"] == 1001
    token = preview.data["token"]
    # A client cannot skip uncommitted rows or change the approved subset.
    assert (
        upload(
            admin_client, "contacts", content, action="commit", token=token, start=100
        ).status_code
        == 400
    )
    for _ in range(2):
        result = upload(
            admin_client, "contacts", content, action="commit", token=token, start=0
        )
        assert result.status_code == 200, result.data
        assert result.data["created"] == 100
        assert not result.data["complete"]
    assert target_model("Contact").objects.filter(org=org_a).count() == 100
    result = upload(
        admin_client, "contacts", content, action="commit", token=token, start=100
    )
    assert result.status_code == 200, result.data
    assert result.data["created"] == 200 and result.data["complete"]
    assert result.data["skipped"] == 800
    assert target_model("Contact").objects.filter(org=org_a).count() == 200


def test_corrected_error_report_can_be_reuploaded(admin_client, org_a):
    content = 'first_name,email,__import_row,__import_errors\nCorrected,corrected@example.com,10,"email: invalid"\n'
    preview = upload(admin_client, "contacts", content)
    assert preview.data["valid"] == 1, preview.data
    result = upload(
        admin_client, "contacts", content, action="commit", token=preview.data["token"]
    )
    assert result.status_code == 200, result.data
    assert (
        target_model("Contact").objects.get(org=org_a).email == "corrected@example.com"
    )


def test_later_batch_failure_preserves_progress_and_resumes(admin_client, org_a):
    from rest_framework.response import Response

    from contacts.views import ContactsListView

    content = "first_name\n" + "\n".join(f"Person {i}" for i in range(102))
    token = upload(admin_client, "contacts", content).data["token"]
    first = upload(admin_client, "contacts", content, action="commit", token=token)
    assert first.data["created"] == 100
    original = ContactsListView.post

    def fail_last(view, request):
        if request.data["first_name"] == "Person 101":
            return Response(
                {"errors": {"first_name": "Concurrent conflict"}}, status=400
            )
        return original(view, request)

    with patch.object(ContactsListView, "post", fail_last):
        response = upload(
            admin_client, "contacts", content, action="commit", token=token, start=100
        )
    assert response.status_code == 400
    assert target_model("Contact").objects.filter(org=org_a).count() == 100
    assert CSVImportReceipt.objects.get(org=org_a).created_count == 100
    retry = upload(
        admin_client, "contacts", content, action="commit", token=token, start=100
    )
    assert retry.status_code == 200, retry.data
    assert retry.data["created"] == 102 and retry.data["complete"]


@pytest.mark.parametrize(
    "module,content,field",
    [
        (
            "contacts",
            "first_name,email,phone\nFirst,one@example.com,+13055550199\nSecond,two@example.com,3055550199\n",
            "phone",
        ),
        (
            "contacts",
            "first_name,email\nFirst,one@example.com\nSecond,ONE@example.com\n",
            "email",
        ),
        (
            "companies",
            "name,website\nFirst,https://www.example.com/about\nSecond,http://example.com?ref=1\n",
            "website",
        ),
    ],
)
def test_import_duplicate_identity_keys(admin_client, module, content, field):
    result = upload(admin_client, module, content)
    assert result.status_code == 200, result.data
    assert result.data["valid"] == 1, result.data
    assert result.data["errors"][0]["field"] == field
    response = upload(
        admin_client, module, content, action="commit", token=result.data["token"]
    )
    assert response.status_code == 200, response.data


def test_company_import_allows_shared_name_with_distinct_domains(admin_client, org_a):
    content = "name,website\nSame,https://first.example.com\nSame,https://second.example.com\n"
    result = upload(admin_client, "companies", content)
    assert result.data["valid"] == 2, result.data
    response = upload(
        admin_client, "companies", content, action="commit", token=result.data["token"]
    )
    assert response.status_code == 200, response.data
    assert target_model("Account").objects.filter(org=org_a, name="Same").count() == 2


def test_rejected_row_does_not_reserve_its_other_identifiers(admin_client):
    content = "first_name,email,phone\nOne,one@example.com,+13055550199\nRejected,two@example.com,+13055550199\nTwo,two@example.com,+13055550188\n"
    result = upload(admin_client, "contacts", content)
    assert result.data["valid"] == 2, result.data
    assert {e["row"] for e in result.data["errors"]} == {3}


@pytest.mark.parametrize(
    "module,content,missing",
    [
        ("contacts", "first_name\nMissing\n", {"email", "phone"}),
        ("companies", "name\nMissing\n", {"website"}),
    ],
)
def test_csv_requires_system_identity(admin_client, module, content, missing):
    result = upload(admin_client, module, content, complete_identity=False)
    assert result.status_code == 200
    assert result.data["valid"] == 0
    assert missing.issubset({e["field"] for e in result.data["errors"]})


@pytest.mark.parametrize(
    "key,value", [("email", "only-email@example.com"), ("phone", "+12025550123")]
)
def test_import_follows_configurable_contact_identity(admin_client, org_a, key, value):
    from contacts.models import Contact

    org_a.creation_forms = {
        "Contact": [
            {"key": "first_name", "required": True},
            {"key": key, "required": True},
        ]
    }
    org_a.save(update_fields=["creation_forms"])
    meta = admin_client.get("/api/record-import/contacts/")
    assert meta.status_code == 200
    content = f"first_name,{key}\nConfigured,{value}\n"
    preview = upload(admin_client, "contacts", content, complete_identity=False)
    assert preview.status_code == 200, preview.data
    assert preview.data["errors"] == [], preview.data
    committed = upload(
        admin_client,
        "contacts",
        content,
        complete_identity=False,
        action="commit",
        token=preview.data["token"],
    )
    assert committed.status_code == 200, committed.data
    assert committed.data["created"] == 1
    contact = Contact.objects.get(org=org_a, first_name="Configured")
    assert getattr(contact, key) == value
    assert not getattr(contact, "phone" if key == "email" else "email")
