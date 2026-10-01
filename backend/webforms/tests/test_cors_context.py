"""CORS preflights finish before the normal tenant-context middleware."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.db import connection

from common.rls.context import org_context
from common.testing import set_rls_context
from webforms.cors import allow_webform_origin

pytestmark = [pytest.mark.django_db, pytest.mark.postgres_only]


def current_org():
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.current_org', true)")
        return cursor.fetchone()[0]


def test_scoped_lookup_restores_previous_tenant(org_a, org_b):
    set_rls_context(org_a)
    with org_context(org_b.pk):
        assert current_org() == str(org_b.pk)
    assert current_org() == str(org_a.pk)
    with pytest.raises(RuntimeError), org_context(org_b.pk):
        raise RuntimeError("Lookup failed")
    assert current_org() == str(org_a.pk)


def test_preflight_restores_context_on_lookup_failure(org_a, org_b):
    set_rls_context(org_a)
    request = SimpleNamespace(
        path=f"/api/public/forms/{org_b.pk}/{org_b.pk}/submit/",
        META={"HTTP_ORIGIN": "https://example.test"},
    )
    with patch(
        "webforms.cors.WebForm.objects.filter",
        side_effect=RuntimeError("Lookup failed"),
    ):
        assert not allow_webform_origin(None, request)
    assert current_org() == str(org_a.pk)
