from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connections

from accounts.models import Account
from common.identifiers import COMPACT_ID_RE, normalize_identifier
from common.models import BusinessIDSequence, LegacyBusinessID, User
from common.rls.context import org_context
from contacts.models import Contact

pytestmark = pytest.mark.django_db


def test_previews_do_not_allocate_and_deleted_ids_are_not_reused(org_a):
    before = (
        BusinessIDSequence.objects.filter(pk="CON")
        .values_list("last_number", flat=True)
        .first()
    )
    assert Contact(org=org_a, first_name="Preview").pk is None
    assert (
        BusinessIDSequence.objects.filter(pk="CON")
        .values_list("last_number", flat=True)
        .first()
        == before
    )
    first = Contact.objects.create(org=org_a, first_name="First")
    original = first.pk
    first.delete()
    second = Contact.objects.create(org=org_a, first_name="Second")
    assert second.pk.startswith("CON-")
    assert int(second.pk[4:]) > int(original[4:])


def test_sequence_is_global_and_expands_beyond_four_digits(org_a, org_b):
    BusinessIDSequence.objects.update_or_create(
        pk="COM", defaults={"last_number": 9999}
    )
    with org_context(org_a.pk):
        first = Account.objects.create(org=org_a, name="First")
    with org_context(org_b.pk):
        second = Account.objects.create(org=org_b, name="Second")
    assert first.pk == "COM-10000"
    assert second.pk == "COM-10001"


def test_organization_ids_are_opaque_and_user_ids_are_short(org_a, admin_user):
    assert COMPACT_ID_RE.fullmatch(org_a.pk)
    assert len(org_a.pk) == 12
    assert admin_user.pk.startswith("USR-")
    assert COMPACT_ID_RE.fullmatch(admin_user.pk)


def test_old_links_resolve_but_cannot_cross_tenants(admin_client, org_a, org_b):
    from uuid import uuid4

    own = Contact.objects.create(org=org_a, first_name="Own")
    with org_context(org_b.pk):
        foreign = Contact.objects.create(org=org_b, first_name="Foreign")
    for record, expected in [(own, 200), (foreign, 404)]:
        old = str(uuid4())
        LegacyBusinessID.objects.create(pk=old, replacement=record.pk)
        response = admin_client.get(f"/api/contacts/{old}/")
        assert response.status_code == expected
    assert admin_client.get(f"/api/contacts/{own.pk}/").status_code == 200


def test_queued_legacy_references_resolve_through_primary_and_foreign_keys(org_a):
    from uuid import uuid4

    old_org, old_contact = str(uuid4()), str(uuid4())
    contact = Contact.objects.create(org=org_a, first_name="Queued reference")
    LegacyBusinessID.objects.create(pk=old_org, replacement=org_a.pk)
    LegacyBusinessID.objects.create(pk=old_contact, replacement=contact.pk)
    assert Contact.objects.get(pk=old_contact, org_id=old_org).pk == contact.pk


def test_signed_session_keeps_the_same_user_and_organization(
    admin_user, admin_profile, org_a
):
    from uuid import uuid4

    from rest_framework.test import APIClient

    from common.serializer import OrgAwareRefreshToken

    old_user, old_org = str(uuid4()), str(uuid4())
    LegacyBusinessID.objects.create(pk=old_user, replacement=admin_user.pk)
    LegacyBusinessID.objects.create(pk=old_org, replacement=org_a.pk)
    token = OrgAwareRefreshToken.for_user_and_org(admin_user, org_a, admin_profile)
    token["user_id"] = old_user
    token["org_id"] = old_org
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    response = client.get("/api/auth/me/")
    assert response.status_code == 200, response.data
    assert response.data["id"] == admin_user.pk
    assert org_a.pk in [row["id"] for row in response.data["organizations"]]
    contact = Contact.objects.create(org=org_a, first_name="Session scope")
    assert client.get(f"/api/contacts/{contact.pk}/").status_code == 200
    refresh = client.post(
        "/api/auth/refresh-token/", {"refresh": str(token)}, format="json"
    )
    assert refresh.status_code == 200, refresh.data
    from rest_framework_simplejwt.tokens import AccessToken

    rotated = AccessToken(refresh.data["access"])
    assert rotated["user_id"] == admin_user.pk
    assert rotated["org_id"] == org_a.pk


def test_ticket_email_subjects_resolve_compact_and_legacy_ids(org_a, org_b):
    from types import SimpleNamespace

    from cases.inbound.threading import find_existing_case
    from cases.models import Case

    case = Case.objects.create(org=org_a, name="Existing conversation")
    old_id = "12345678-1234-4234-8234-123456789abc"
    LegacyBusinessID.objects.create(pk=old_id, replacement=case.pk)
    for subject_id in [case.pk, old_id[:8]]:
        message = SimpleNamespace(
            in_reply_to="", references=[], subject=f"Re: [Case #{subject_id}]"
        )
        assert find_existing_case(message, org_a).pk == case.pk
        with org_context(org_b.pk):
            assert find_existing_case(message, org_b) is None


@pytest.mark.parametrize(
    "value", ["ORG001", "CON-1", "HDM-OOOOOOOO", "con-0001", "CON-0001/", "CON-0001\n"]
)
def test_rejects_malformed_ids(value):
    with pytest.raises(ValueError):
        normalize_identifier(value)


@pytest.mark.postgres_only
@pytest.mark.django_db(transaction=True)
def test_concurrent_id_allocation_is_unique():
    def create(number):
        try:
            return User.objects.create_user(email=f"parallel-{number}@example.com").pk
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=6) as pool:
        ids = list(pool.map(create, range(24)))
    assert len(set(ids)) == 24
    assert all(COMPACT_ID_RE.fullmatch(pk) for pk in ids)
