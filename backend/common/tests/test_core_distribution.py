"""The main build must not expose or schedule the archived Review modules."""

from types import SimpleNamespace

import pytest
from django.urls import Resolver404, resolve

from common.platform_access import can_preview
from crm.celery import app

ARCHIVED_URLS = (
    "/api/leads/",
    "/api/invoices/",
    "/api/documents/",
    "/api/packs/",
    "/api/opportunities/goals/",
    "/api/business-hours/",
    "/api/macros/",
    "/api/cases/routing-rules/",
    "/api/cases/escalation-policies/",
    "/api/cases/mailboxes/",
    "/api/cases/approval-rules/",
    "/api/time-entries/",
    "/api/profile/tokens/",
    "/api/org/tokens/",
    "/api/api-settings/",
)


@pytest.mark.parametrize("url", ARCHIVED_URLS)
def test_archived_routes_are_not_registered(url):
    with pytest.raises(Resolver404):
        resolve(url)


@pytest.mark.django_db
@pytest.mark.parametrize("url", ARCHIVED_URLS)
def test_even_platform_owner_cannot_open_archived_routes(admin_client, admin_user, url):
    admin_user.is_superuser = True
    admin_user.save()
    assert admin_client.get(url).status_code == 404


@pytest.mark.parametrize(
    "url",
    (
        "/api/contacts/",
        "/api/accounts/",
        "/api/opportunities/",
        "/api/tasks/",
        "/api/cases/",
        "/api/notifications/",
        "/api/webforms/",
        "/api/reports/crm/",
        "/api/roles/",
        "/api/integrations/google/",
        "/api/sales-appointments/",
    ),
)
def test_active_routes_remain_registered(url):
    assert resolve(url).func is not None


def test_owner_has_no_preview_exception():
    profile = SimpleNamespace(
        is_demo=False, user=SimpleNamespace(is_active=True, is_superuser=True)
    )
    assert can_preview(profile) is False


def test_beat_only_schedules_active_workflows():
    scheduled = {entry["task"] for entry in app.conf.beat_schedule.values()}
    assert scheduled == {
        "common.tasks.purge_deleted_attachment_files",
        "common.tasks.send_due_reminders",
        "webforms.tasks.retry_pending_webform_emails",
        "common.tasks.schedule_google_sync",
        "opportunity.tasks.check_stale_opportunities",
        "common.tasks.purge_read_notifications",
        "common.tasks.flush_expired_refresh_tokens",
    }


def test_worker_does_not_register_review_jobs():
    app.autodiscover_tasks(force=True)
    app.finalize()
    assert not any(name.startswith("invoices.") for name in app.tasks)
    assert "opportunity.tasks.check_goal_milestones" not in app.tasks
    assert "cases.tasks.scan_for_breached_cases" not in app.tasks
    assert "cases.tasks.auto_stop_stale_timers" not in app.tasks
    assert "leads.tasks.send_lead_assigned_emails" not in app.tasks
    # Old queued generic mail can still drain safely on a rolling deploy.
    assert "leads.tasks.send_email" in app.tasks
