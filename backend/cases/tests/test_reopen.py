"""
Tests for the Tier-1 reopen feature: cases/signals.py auto-reopen on customer
reply + ReopenPolicy API.

See docs/cases/tier1/reopen.md.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from cases.models import ReopenPolicy
from common.models import Activity, Comment
from conftest import rls_org


def _close_case(case, *, days_ago=1):
    """Close a case and backdate closed_on to simulate elapsed time."""
    case.status = "Closed"
    case.closed_on = timezone.localdate() - timedelta(days=days_ago)
    # Used on both tenants' cases by the org-scoping test, and the isolation
    # policy governs UPDATE as well as INSERT.
    with rls_org(case.org):
        case.save()
    return case


def _post_external_comment(case, *, text="customer reply"):
    """Simulate a customer/email-to-ticket comment (no commented_by)."""
    # `comment` is org-scoped and this helper is used on both tenants' cases
    # by the org-scoping test.
    with rls_org(case.org):
        return Comment.objects.create(
            comment=text,
            content_type=ContentType.objects.get_for_model(case),
            object_id=case.pk,
            commented_by=None,
            is_internal=False,
            org=case.org,
        )


def _latest_activity(case, action):
    return (
        Activity.objects.filter(entity_type="Case", entity_id=case.pk, action=action)
        .order_by("-created_at")
        .first()
    )


@pytest.mark.django_db
class TestReopenSignal:
    def test_external_reply_within_window_reopens(self, case_a):
        _close_case(case_a, days_ago=2)
        _post_external_comment(case_a)

        case_a.refresh_from_db()
        assert case_a.status == "Pending"
        assert case_a.closed_on is None

        reopened = _latest_activity(case_a, "REOPENED")
        assert reopened is not None
        assert reopened.metadata.get("to_status") == "Pending"
        assert reopened.metadata.get("days_since_close") == 2

    def test_external_reply_out_of_window_does_not_reopen(self, case_a):
        _close_case(case_a, days_ago=30)
        _post_external_comment(case_a)

        case_a.refresh_from_db()
        assert case_a.status == "Closed"
        # The COMMENT activity row carries the out_of_reopen_window flag.
        comment_row = _latest_activity(case_a, "COMMENT")
        assert comment_row is not None
        assert comment_row.metadata.get("out_of_reopen_window") is True
        # No REOPENED row was emitted.
        assert _latest_activity(case_a, "REOPENED") is None

    def test_agent_comment_does_not_reopen(self, case_a, admin_profile):
        _close_case(case_a, days_ago=2)
        Comment.objects.create(
            comment="cleanup note",
            content_type=ContentType.objects.get_for_model(case_a),
            object_id=case_a.pk,
            commented_by=admin_profile,
            is_internal=False,
            org=case_a.org,
        )

        case_a.refresh_from_db()
        assert case_a.status == "Closed"
        assert _latest_activity(case_a, "REOPENED") is None

    def test_internal_external_comment_does_not_reopen(self, case_a):
        # commented_by=None but is_internal=True should still not reopen.
        # Realistically internal notes always have commented_by, but the
        # gating must still work if both flags somehow agree.
        _close_case(case_a, days_ago=2)
        Comment.objects.create(
            comment="internal cleanup",
            content_type=ContentType.objects.get_for_model(case_a),
            object_id=case_a.pk,
            commented_by=None,
            is_internal=True,
            org=case_a.org,
        )

        case_a.refresh_from_db()
        assert case_a.status == "Closed"

    def test_non_closed_status_does_not_reopen(self, case_a):
        # Rejected and Duplicate should NOT reopen even on an external reply.
        case_a.status = "Rejected"
        case_a.closed_on = timezone.localdate() - timedelta(days=2)
        case_a.save()

        _post_external_comment(case_a)

        case_a.refresh_from_db()
        assert case_a.status == "Rejected"
        assert _latest_activity(case_a, "REOPENED") is None

    def test_policy_disabled_blocks_reopen(self, case_a, org_a):
        ReopenPolicy.objects.create(org=org_a, is_enabled=False)
        _close_case(case_a, days_ago=2)

        _post_external_comment(case_a)

        case_a.refresh_from_db()
        assert case_a.status == "Closed"
        assert _latest_activity(case_a, "REOPENED") is None

    def test_policy_window_is_honored(self, case_a, org_a):
        ReopenPolicy.objects.create(
            org=org_a, is_enabled=True, reopen_window_days=3, reopen_to_status="Pending"
        )
        _close_case(case_a, days_ago=5)

        _post_external_comment(case_a)
        case_a.refresh_from_db()
        assert case_a.status == "Closed"

        # Try a fresh case within the new window.
        case_a.status = "Closed"
        case_a.closed_on = timezone.localdate() - timedelta(days=2)
        case_a.save()
        _post_external_comment(case_a)
        case_a.refresh_from_db()
        assert case_a.status == "Pending"

    def test_custom_reopen_status(self, case_a, org_a):
        ReopenPolicy.objects.create(
            org=org_a, is_enabled=True, reopen_to_status="Assigned"
        )
        _close_case(case_a, days_ago=1)
        _post_external_comment(case_a)
        case_a.refresh_from_db()
        assert case_a.status == "Assigned"
