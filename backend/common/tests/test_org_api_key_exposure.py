"""Regression tests for org API-key exposure (user -> admin privilege escalation).

The org `api_key` authenticates its bearer as the org's first ADMIN profile
(see `common.external_auth.APIKeyAuthentication`). It must therefore never
appear in ordinary API responses, which any org member -- including
role="USER" -- is entitled to read.
"""

import json

import pytest

from accounts.models import Account
from cases.models import Case
from common.serializer import OrganizationSerializer
from contacts.models import Contact
from opportunity.models import Opportunity

ORG_API_KEY_URL = "/api/org/api-key/"


def _payload_contains(response, needle):
    """True if `needle` appears anywhere in the serialized response body."""
    return needle in json.dumps(response.json())


@pytest.fixture
def visible_records(org_a, user_profile):
    """Records assigned to the USER-role profile, so they appear in its lists.

    Without the assignment the list endpoints return nothing for that profile
    and a leak assertion would pass vacuously.
    """
    account = Account.objects.create(name="Acme Corp", org=org_a)
    contact = Contact.objects.create(
        first_name="Jane", last_name="Doe", email="jane@acme.test", org=org_a
    )
    contact.assigned_to.add(user_profile)
    opportunity = Opportunity.objects.create(
        name="Acme Deal", org=org_a, account=account
    )
    opportunity.assigned_to.add(user_profile)
    case = Case.objects.create(name="Acme Issue", org=org_a, account=account)
    case.assigned_to.add(user_profile)
    return {"account": account, "contact": contact, "opportunity": opportunity}


# Endpoints confirmed to nest OrganizationSerializer in their responses.
LEAKY_ENDPOINTS = [
    "/api/contacts/",
    "/api/opportunities/",
    "/api/cases/",
]


class TestSerializerDoesNotExposeApiKey:
    def test_organization_serializer_excludes_api_key(self, org_a):
        data = OrganizationSerializer(org_a).data
        assert "api_key" not in data


class TestApiKeyNotLeakedToOrgMembers:
    """A USER-role member must not be able to read the org api_key."""

    @pytest.mark.parametrize("endpoint", LEAKY_ENDPOINTS)
    def test_endpoint_does_not_leak_api_key_to_user_role(
        self, user_client, org_a, visible_records, endpoint
    ):
        response = user_client.get(endpoint)
        assert response.status_code == 200
        assert not _payload_contains(response, org_a.api_key)

    @pytest.mark.parametrize("endpoint", LEAKY_ENDPOINTS)
    def test_endpoint_does_not_leak_api_key_to_admin_role(
        self, admin_client, org_a, visible_records, endpoint
    ):
        """Admins get the key from the dedicated endpoint, not incidentally."""
        response = admin_client.get(endpoint)
        assert response.status_code == 200
        assert not _payload_contains(response, org_a.api_key)

    def test_contact_is_actually_visible_to_user(self, user_client, visible_records):
        """Guards the leak assertions above from passing on an empty list."""
        response = user_client.get("/api/contacts/")
        assert _payload_contains(response, visible_records["contact"].email)
