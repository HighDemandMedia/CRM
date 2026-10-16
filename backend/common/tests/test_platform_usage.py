from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.db import connection
from rest_framework.test import APIClient

from common.models import Profile
from common.platform_usage import database_capacity, database_usage, organization_usage
from common.testing import _make_authenticated_client, rls_org
from contacts.models import Contact

pytestmark = pytest.mark.django_db
URL = "/api/platform/usage/"


@pytest.fixture(autouse=True)
def clear_usage_cache(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "platform-usage-tests",
        }
    }
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def owner(admin_user, admin_profile):
    admin_user.is_superuser = True
    admin_user.save(update_fields=["is_superuser"])
    return admin_user, _make_authenticated_client(
        admin_user, admin_profile.org, admin_profile
    )


def test_customer_and_anonymous_cannot_read_usage(admin_client, user_client):
    assert admin_client.get(URL).status_code == 403
    assert user_client.get(URL).status_code == 403
    assert APIClient().get(URL).status_code == 403


def test_revoked_owner_cannot_read_cached_usage(owner):
    user, client = owner
    assert client.get(URL).status_code == 200
    user.is_superuser = False
    user.save(update_fields=["is_superuser"])
    assert client.get(URL).status_code == 403
    assert client.get("/api/org/ui-context/").data["is_platform_owner"] is False


def test_cross_tenant_counts_are_isolated_and_do_not_return_records(
    owner, org_a, org_b
):
    _, client = owner
    with rls_org(org_a):
        Contact.objects.create(org=org_a, first_name="Private Alpha")
    with rls_org(org_b):
        Contact.objects.create(org=org_b, first_name="Private Beta")
        Contact.objects.create(org=org_b, first_name="Private Gamma")
    response = client.get(URL)
    assert response.status_code == 200, response.content
    rows = {row["id"]: row for row in response.data["results"]}
    assert rows[str(org_a.pk)]["contacts"] == 1
    assert rows[str(org_b.pk)]["contacts"] == 2
    assert b"Private Alpha" not in response.content
    assert response["Cache-Control"] == "private, no-store"
    # The temporary tenant context must not leak back into the caller's context.
    with rls_org(org_a):
        organization_usage(org_b)
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_setting('app.current_org', true)")
                assert cursor.fetchone()[0] == str(org_a.pk)


def test_pagination_and_search_are_bounded(owner, org_b):
    _, client = owner
    response = client.get(URL, {"q": org_b.name, "page_size": 10})
    assert response.status_code == 200
    assert any(row["id"] == str(org_b.pk) for row in response.data["results"])
    assert client.get(URL, {"page_size": 10000}).status_code == 400
    assert client.get(URL, {"offset": -1}).status_code == 400
    assert client.get(URL, {"q": "x" * 101}).status_code == 400
    assert client.get(URL, {"offset": 1000}).data["results"] == []


def test_support_and_removed_members_are_excluded(org_a, admin_profile):
    before = organization_usage(org_a)["users"]
    Profile.objects.filter(pk=admin_profile.pk).update(is_platform_access=True)
    cache.clear()
    assert organization_usage(org_a)["users"] == before - 1


def test_cached_counts_do_not_query_again(org_a, django_assert_num_queries):
    organization_usage(org_a)
    with django_assert_num_queries(0):
        organization_usage(org_a)


def test_database_size_is_not_invented_for_sqlite():
    with patch.object(connection, "vendor", "sqlite"):
        result = database_usage()
        assert result["bytes"] is None
        assert result["measured_at"] is None
        assert result["remaining_estimated_bytes"] is None


@pytest.mark.parametrize(
    "capacity,used,remaining",
    [
        (1000, 250, 750),
        (1000, 1200, 0),
        (0, 250, None),
        (1000, None, None),
        (-1, 250, None),
    ],
)
def test_capacity_never_fabricates_available_space(settings, capacity, used, remaining):
    settings.CRM_DATABASE_CAPACITY_BYTES = capacity
    result = database_capacity(used)
    assert result["total_bytes"] == (capacity if capacity > 0 else None)
    assert result["remaining_estimated_bytes"] == remaining


def test_capacity_changes_apply_even_with_cached_database_measurement(settings):
    settings.CRM_DATABASE_CAPACITY_BYTES = 1000
    cache.set(
        "platform-usage:v1:database",
        {"bytes": 250, "measured_at": "2026-10-16T12:00:00Z"},
    )
    with patch.object(connection, "vendor", "postgresql"):
        assert database_usage()["remaining_estimated_bytes"] == 750
        settings.CRM_DATABASE_CAPACITY_BYTES = 2000
        assert database_usage()["remaining_estimated_bytes"] == 1750


@pytest.mark.parametrize(
    "used,status",
    [
        (0, "normal"),
        (699, "normal"),
        (700, "plan"),
        (799, "plan"),
        (800, "expand"),
        (899, "expand"),
        (900, "critical"),
        (1200, "critical"),
        (None, "unknown"),
    ],
)
def test_capacity_alert_boundaries(settings, used, status):
    settings.CRM_DATABASE_CAPACITY_BYTES = 1000
    result = database_capacity(used)
    assert result["capacity_status"] == status
    assert result["used_percent"] == (used / 10 if used is not None else None)


def test_unknown_capacity_never_reports_healthy(settings):
    settings.CRM_DATABASE_CAPACITY_BYTES = 0
    result = database_capacity(250)
    assert result["capacity_status"] == "unknown"
    assert result["used_percent"] is None
