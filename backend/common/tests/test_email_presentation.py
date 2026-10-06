import pytest
from django.template.loader import render_to_string


@pytest.mark.parametrize(
    "template",
    [
        "emails/invitation.html",
        "emails/support_request.html",
        "portal/login_email.html",
        "portal/case_update_email.html",
        "webforms/submission_email.html",
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
            "user": {"first_name": "Test User", "get_username": "test@example.com"},
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
            "submission": {"payload": {"<script>": "<img src=x onerror=alert(1)>"}},
        },
    )
    assert "<img src=x" not in html and "&lt;img src=x" in html
