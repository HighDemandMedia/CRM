from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.template.loader import render_to_string

from common.invitations import send_invitation
from common.models import User


@pytest.mark.parametrize(
    "template",
    [
        "emails/invitation.html",
        "emails/appointment.html",
        "emails/support_request.html",
        "portal/login_email.html",
        "portal/case_update_email.html",
        "webforms/submission_email.html",
        "webforms/confirmation_email.html",
        "magic_link_email.html",
        "magic_link_code_email.html",
        "welcome_email.html",
        "assigned_to/contact_assigned.html",
        "assigned_to/account_assigned.html",
        "assigned_to/cases_assigned.html",
        "assigned_to/opportunity_assigned.html",
        "tasks_email_template.html",
        "csat/survey_email.html",
        "opportunity/stale_deals_alert.html",
        "user_delete_email.html",
        "user_status_activate.html",
        "user_status_deactivate.html",
        "user_status_in.html",
    ],
)
def test_system_email_uses_shared_theme(template):
    html = render_to_string(
        template,
        {
            "user": User(name="Test User", email="test@example.com"),
            "form": {"name": "Contact", "target_model": "Contact"},
            "submission": {"payload": {}},
        },
    )
    assert "High Demand Media" in html
    assert "background-color:#292D30" in html
    assert "background-color:#C82322" in html
    assert "linear-gradient(135deg,#AC0F0B,#CA4618)" in html
    assert "background-color:;" not in html


def test_invitation_preserves_link_and_escapes_customer_name():
    html = render_to_string(
        "emails/invitation.html",
        {
            "organization": "<script>alert(1)</script>",
            "email": "new@example.com",
            "link": "https://crm.example/invite?token=safe",
        },
    )
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert 'href="https://crm.example/invite?token=safe"' in html


def test_webform_email_escapes_submitted_content():
    html = render_to_string(
        "webforms/submission_email.html",
        {
            "form": {"name": "Contact"},
            "submission_rows": [
                {"label": "<script>", "value": "<img src=x onerror=alert(1)>"}
            ],
        },
    )
    assert "<img src=x" not in html and "&lt;img src=x" in html


@pytest.mark.parametrize("owner", [True, False])
def test_invitation_explains_the_matching_onboarding(owner):
    sender = Mock(return_value=1)
    row = SimpleNamespace(
        org=SimpleNamespace(name="Example Team"),
        email="new@example.com",
        grants_ownership=owner,
    )
    send_invitation(row, "test-token", sender=sender)
    sender.assert_called_once()
    message = sender.call_args.args[1]
    html = sender.call_args.kwargs["html_message"]
    assert sender.call_args.args[3] == [row.email]
    for content in (message, html):
        assert "create your own password" in content
        assert "7 days" in content
        assert "/invite?token=test-token" in content
        assert "complete your profile" in content
    assert ("Congratulations — welcome to your CRM!" in html) is owner
    assert ("Join your team" in html) is not owner
    for content in (message, html):
        assert ("specialized CRM, developed by High Demand Media" in content) is owner
        assert ("Activate your account" in content) is owner
    assert sender.call_args.args[0] == (
        "Welcome to your CRM · High Demand Media"
        if owner
        else "Invitation to Example Team · High Demand Media CRM"
    )


@pytest.mark.parametrize(
    "template,label",
    [
        ("contact_assigned.html", "Contact"),
        ("account_assigned.html", "Company"),
        ("opportunity_assigned.html", "Deal"),
        ("cases_assigned.html", "Ticket"),
    ],
)
@pytest.mark.parametrize("name", ["Ana <Sales>", "", "   "])
def test_assignment_uses_display_name_and_does_not_misidentify_assigner(
    template, label, name
):
    html = render_to_string(
        f"assigned_to/{template}",
        {
            "user": User(name=name, email="ana@example.com"),
            # The record creator is not necessarily the person reassigning it.
            "created_by": "original-creator@example.com",
            "url": "https://crm.example/record/123",
        },
    )
    assert "Ana &lt;Sales&gt;" in html if name.strip() else "ana@example.com" in html
    assert "original-creator@example.com" not in html
    assert f"View {label}" in html
    assert 'href="https://crm.example/record/123"' in html
