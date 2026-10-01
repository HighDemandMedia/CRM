from datetime import timedelta

import pytest
from django.db import connection
from django.test import Client, RequestFactory
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed

from common.models import Org, PersonalAccessToken
from common.pat_auth import PATAuthentication


@pytest.mark.django_db
class TestPATAuthentication:
    def setup_method(self):
        self.factory = RequestFactory()
        self.auth = PATAuthentication()

    def test_no_header_returns_none(self):
        req = self.factory.get("/api/leads/")
        assert self.auth.authenticate(req) is None

    def test_non_pat_bearer_returns_none(self):
        req = self.factory.get("/api/leads/", HTTP_AUTHORIZATION="Bearer ey.some.jwt")
        assert self.auth.authenticate(req) is None

    def test_valid_pat_authenticates_as_owner(self, org_a, admin_user, admin_profile):
        raw, pat = PersonalAccessToken.generate(profile=admin_profile, name="cli")
        req = self.factory.get("/api/leads/", HTTP_AUTHORIZATION=f"Bearer {raw}")
        user, _ = self.auth.authenticate(req)
        assert user == admin_user
        assert req.profile == admin_profile
        assert req.org == org_a
        assert req.META["org"] == str(org_a.id)
        pat.refresh_from_db()
        assert pat.last_used_at is not None

    def test_revoked_pat_raises(self, admin_profile):
        raw, pat = PersonalAccessToken.generate(profile=admin_profile, name="cli")
        pat.revoked_at = timezone.now()
        pat.save()
        req = self.factory.get("/api/leads/", HTTP_AUTHORIZATION=f"Bearer {raw}")
        with pytest.raises(AuthenticationFailed):
            self.auth.authenticate(req)

    def test_expired_pat_raises(self, admin_profile):
        raw, _ = PersonalAccessToken.generate(
            profile=admin_profile,
            name="cli",
            expires_at=timezone.now() - timedelta(days=1),
        )
        req = self.factory.get("/api/leads/", HTTP_AUTHORIZATION=f"Bearer {raw}")
        with pytest.raises(AuthenticationFailed):
            self.auth.authenticate(req)

    def test_unknown_pat_raises(self):
        req = self.factory.get("/api/leads/", HTTP_AUTHORIZATION="Bearer bcrm_pat_nope")
        with pytest.raises(AuthenticationFailed):
            self.auth.authenticate(req)

    def test_inactive_profile_raises(self, admin_profile):
        raw, _ = PersonalAccessToken.generate(profile=admin_profile, name="cli")
        admin_profile.is_active = False
        admin_profile.save()
        req = self.factory.get("/api/leads/", HTTP_AUTHORIZATION=f"Bearer {raw}")
        with pytest.raises(AuthenticationFailed):
            self.auth.authenticate(req)

    def test_valid_pat_via_token_header(self, org_a, admin_user, admin_profile):
        raw, _ = PersonalAccessToken.generate(profile=admin_profile, name="cli")
        req = self.factory.get("/api/leads/", HTTP_TOKEN=raw)
        user, _ = self.auth.authenticate(req)
        assert user == admin_user
        assert req.profile == admin_profile

    def test_inactive_org_raises(self, org_a, admin_profile):
        raw, _ = PersonalAccessToken.generate(profile=admin_profile, name="cli")
        org = admin_profile.org
        org.is_active = False
        org.save()
        req = self.factory.get("/api/leads/", HTTP_AUTHORIZATION=f"Bearer {raw}")
        with pytest.raises(AuthenticationFailed):
            self.auth.authenticate(req)

    def test_last_used_at_throttled_not_rewritten(self, admin_profile):
        raw, pat = PersonalAccessToken.generate(profile=admin_profile, name="cli")
        req = self.factory.get("/api/leads/", HTTP_AUTHORIZATION=f"Bearer {raw}")
        self.auth.authenticate(req)
        pat.refresh_from_db()
        first = pat.last_used_at
        assert first is not None
        # Second auth immediately after, within the 60s throttle window, must not rewrite
        self.auth.authenticate(req)
        pat.refresh_from_db()
        assert pat.last_used_at == first


@pytest.mark.postgres_only
@pytest.mark.django_db
def test_cross_org_pat_cannot_read_other_orgs_contacts(org_a, admin_profile):
    """A PAT scoped to org A must never surface org B's contacts.

    This is the regression guard for tenant isolation through a real list
    endpoint: RLS plus the explicit `org=` ORM filter must keep org B's row
    out of the response. Postgres-only because RLS is enforced by the DB;
    on SQLite it cleanly skips.
    """
    if connection.vendor != "postgresql":
        pytest.skip(
            "RLS isolation is enforced by PostgreSQL; skipping on non-Postgres DB"
        )

    from common.tasks import clear_rls_context, set_rls_context
    from contacts.models import Contact

    # Create org B and a contact in it directly, with org explicitly set.
    #
    # The context has to be set for the INSERT itself. `contact` carries an
    # RLS insert-check policy, so a write with `app.current_org` empty is
    # refused outright ("new row violates row-level security policy"), and
    # this test then failed during its own setup. It went unnoticed because
    # the only role that had ever run it was a Postgres superuser, which
    # bypasses RLS: the guard was inert exactly where it was meant to bite.
    # Cleared again afterwards so the request below is judged on the context
    # the PAT's middleware sets, not one left behind here.
    org_b = Org.objects.create(name="Cross-Org Isolation Org B")
    set_rls_context(org_b.id)
    try:
        contact_b = Contact.objects.create(
            first_name="Hidden",
            last_name="Contact-OrgB",
            email="hidden_orgb@test.com",
            org=org_b,
        )
    finally:
        clear_rls_context()

    set_rls_context(org_a.id)
    visible = Contact.objects.create(org=org_a, first_name="Visible")
    clear_rls_context()
    # Mint a PAT for the org-A admin profile and call the contacts list.
    raw, _ = PersonalAccessToken.generate(profile=admin_profile, name="cross-org-cli")
    client = Client()
    response = client.get("/api/contacts/", HTTP_AUTHORIZATION=f"Bearer {raw}")

    assert response.status_code == 200, response.content
    contact_ids = {row["id"] for row in response.json()["contact_obj_list"]}
    assert str(visible.pk) in contact_ids
    assert str(contact_b.pk) not in contact_ids
