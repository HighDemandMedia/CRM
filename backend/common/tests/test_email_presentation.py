from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.template import Context, Template
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
        "notification_email.html",
        "emails/password_reset.html",
        "emails/password_changed.html",
        "assigned_to/leads_assigned.html",
        "opportunity/goal_milestone.html",
        "invoices/emails/assigned_to_email.html",
        "invoices/emails/invoice_to_client.html",
        "invoices/emails/estimate_to_client.html",
        "invoices/emails/payment_reminder.html",
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


def test_optional_email_sections_do_not_leave_empty_space():
    html = render_to_string("emails/password_changed.html")
    assert 'class="email-section"' not in html
    html = render_to_string("welcome_email.html", {"url": "https://crm.example/"})
    assert html.count('class="email-section"') == 1
    assert 'href="https://crm.example/"' in html


def test_email_section_keeps_template_escaping():
    template = Template(
        "{% load crm_email %}{% email_section %}"
        "<p>{{ message }}</p>{% endemail_section %}"
    )
    html = template.render(Context({"message": '<img src=x onerror="alert(1)">'}))
    assert "<p>&lt;img" in html
    assert "<img" not in html


@pytest.mark.parametrize(
    "kind", ["invoice_to_client", "estimate_to_client", "payment_reminder"]
)
def test_financial_email_preserves_customer_details_and_optional_action(kind):
    from datetime import date

    record = SimpleNamespace(
        client_name="Ana <Sales>",
        invoice_number="INV-123",
        estimate_number="EST-123",
        invoice_title="Website project",
        title="Website project",
        currency="USD",
        amount_due="1200.00",
        total_amount="1800.00",
        issue_date=date(2026, 11, 1),
        due_date=date(2026, 11, 15),
        expiry_date=date(2026, 11, 30),
    )
    context = {
        "org": SimpleNamespace(name="Example Team"),
        "invoice": record,
        "estimate": record,
        "days_overdue": 3,
    }
    path = f"invoices/emails/{kind}.html"
    html = render_to_string(path, context)
    assert "Ana &lt;Sales&gt;" in html
    assert "Example Team" in html and "USD" in html
    assert "Website project" in html
    assert ('class="btn-link"' in html) is False
    url = "https://crm.example/public/document?token=safe&view=1"
    html = render_to_string(path, {**context, "public_url": url})
    assert 'href="https://crm.example/public/document?token=safe&amp;view=1"' in html
    if kind == "payment_reminder":
        assert "3 days overdue" in html


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
