import csv
import io

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from cases.models import Case
from common.csv_utils import csv_safe
from common.models import PersonalAccessToken
from common.views.password_auth_views import PasswordIPThrottle


@pytest.mark.parametrize(
    "value",
    [
        "=1+1",
        "+1",
        "-1",
        "@SUM(1)",
        "\tvalue",
        "\rvalue",
        "\nvalue",
        "\ufeff =1",
        "\u00a0=1",
    ],
)
def test_csv_formula_and_control_prefixes_are_text(value):
    assert csv_safe(value) == "'" + value


@pytest.mark.parametrize(
    "value,expected", [(None, ""), (42, "42"), ("Normal, text", "Normal, text")]
)
def test_csv_preserves_safe_values(value, expected):
    assert csv_safe(value) == expected


@pytest.mark.django_db
def test_ticket_export_neutralizes_formulas(admin_client, org_a):
    Case.objects.create(
        org=org_a,
        name="=1+1",
        status="New",
        priority="Normal",
        first_response_at=timezone.now(),
    )
    response = admin_client.get("/api/cases/analytics/export/?metric=frt")
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(b"".join(response.streaming_content).decode())))
    assert any(row[1] == "'=1+1" for row in rows[1:])


@pytest.mark.parametrize("trusted", [False, True])
def test_forged_prefix_does_not_reset_login_throttle(settings, trusted):
    settings.TRUSTED_PROXY_CIDRS = ("192.0.2.0/24",) if trusted else ()
    cache.clear()
    factory = APIRequestFactory()

    def request(prefix):
        return factory.post(
            "/api/auth/password/login/",
            {},
            REMOTE_ADDR="192.0.2.20",
            HTTP_X_FORWARDED_FOR=f"{prefix}, 198.51.100.10",
        )

    try:
        for _ in range(30):
            assert PasswordIPThrottle().allow_request(request("203.0.113.1"), None)
        assert not PasswordIPThrottle().allow_request(request("203.0.113.2"), None)
    finally:
        cache.clear()


@pytest.mark.django_db
@pytest.mark.parametrize("scopes", [[], ["*:read"], ["platform:read"]])
def test_platform_owner_pat_cannot_access_platform_usage(admin_profile, scopes):
    user = admin_profile.user
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    raw, _ = PersonalAccessToken.generate(
        profile=admin_profile, name="Audit", scopes=scopes
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    assert client.get("/api/platform/usage/").status_code in (401, 403)
