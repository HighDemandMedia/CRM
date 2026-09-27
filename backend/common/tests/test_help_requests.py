import uuid
from unittest.mock import patch

import pytest
from django.core import mail
from django.core.cache import cache
from django.test import override_settings

from common.views.help_views import SUPPORT_EMAIL

URL = "/api/help/requests/"


def payload(category="help"):
    fields = {
        "bug": {
            "steps": "Open a contact then drag it.",
            "impact": "workaround",
            "frequency": "sometimes",
            "actual": "Stage does not update.",
            "expected": "Move to Lead.",
        },
        "feature": {
            "problem": "I reuse report filters.",
            "suggestion": "Save named reports.",
            "benefit": "Less repeated work.",
        },
        "help": {
            "question": "How do I add a pipeline rule?",
            "tried": "Opened Pipelines.",
        },
    }
    return {
        "request_id": str(uuid.uuid4()),
        "category": category,
        "area": "General",
        "subject": "CRM assistance",
        **fields[category],
    }


@pytest.fixture(autouse=True)
def support_mail_settings(settings):
    settings.DEBUG = True
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "crm@example.com"
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestHelpRequests:
    @pytest.mark.parametrize("category", ["bug", "feature", "help"])
    def test_all_forms_send_to_hdm_with_verified_sender(
        self, user_client, user_profile, category
    ):
        data = payload(category)
        data.update(
            {
                "to": "attacker@example.com",
                "reply_to": "fake@example.com",
                "organization": "fake",
                "question": "Unrelated hidden field",
            }
        ) if category != "help" else data.update({"to": "attacker@example.com"})
        response = user_client.post(URL, data, format="json")
        assert response.status_code == 201, response.data
        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.to == [SUPPORT_EMAIL]
        assert message.reply_to == [user_profile.user.email]
        assert str(user_profile.org_id) in message.body
        assert "Unrelated hidden field" not in message.body
        assert "attacker@example.com" not in message.body
        assert response.data["delivery_mode"] == "local_test"
        assert response.data["reference"] in message.body
        headings = {
            "bug": "Steps to reproduce",
            "feature": "Desired outcome",
            "help": "Question / task to accomplish",
        }
        assert headings[category] in message.body

    @pytest.mark.parametrize(
        "category,missing",
        [
            ("bug", "actual"),
            ("bug", "expected"),
            ("bug", "impact"),
            ("feature", "problem"),
            ("feature", "benefit"),
            ("help", "question"),
        ],
    )
    def test_requires_fields_for_selected_objective(
        self, user_client, category, missing
    ):
        data = payload(category)
        data[missing] = " "
        response = user_client.post(URL, data, format="json")
        assert response.status_code == 400
        assert missing in response.data
        assert len(mail.outbox) == 0

    def test_duplicate_submission_sends_once_and_changed_payload_rejected(
        self, admin_client
    ):
        data = payload()
        first = admin_client.post(URL, data, format="json")
        second = admin_client.post(URL, data, format="json")
        assert first.status_code == 201 and second.status_code == 200
        assert first.data["reference"] == second.data["reference"]
        assert len(mail.outbox) == 1
        data["question"] = "A changed question"
        assert admin_client.post(URL, data, format="json").status_code == 409
        assert len(mail.outbox) == 1

    def test_failure_does_not_report_success_and_allows_retry(self, admin_client):
        data = payload()
        with patch(
            "common.views.help_views.EmailMessage.send",
            side_effect=OSError("Unavailable"),
        ):
            assert admin_client.post(URL, data, format="json").status_code == 503
        assert admin_client.post(URL, data, format="json").status_code == 201
        assert len(mail.outbox) == 1

    def test_zero_send_is_not_success(self, admin_client):
        with patch("common.views.help_views.EmailMessage.send", return_value=0):
            assert admin_client.post(URL, payload(), format="json").status_code == 503

    def test_metadata_and_production_without_mail(self, user_client, user_profile):
        response = user_client.get(URL)
        assert response.status_code == 200
        assert response.data["reply_to"] == user_profile.user.email
        assert response.data["delivery_mode"] == "local_test"
        with override_settings(DEBUG=False):
            assert user_client.get(URL).data["delivery_mode"] == "unavailable"
            assert user_client.post(URL, payload(), format="json").status_code == 503
        assert len(mail.outbox) == 0

    def test_smtp_mode_and_subject_single_line(self, admin_client):
        data = payload()
        data["subject"] = "Subject\nBcc: injected"
        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
            EMAIL_HOST="smtp.example.com",
        ):
            with patch(
                "common.views.help_views.EmailMessage.send", return_value=1
            ) as send:
                response = admin_client.post(URL, data, format="json")
                assert response.status_code == 201, response.data
                assert response.data["delivery_mode"] == "email"
                assert send.call_count == 1

    def test_auth_and_rate_limit(self, unauthenticated_client, admin_client):
        assert unauthenticated_client.post(
            URL, payload(), format="json"
        ).status_code in (401, 403)
        with patch("common.views.help_views.EmailMessage.send", return_value=1):
            for _ in range(10):
                assert (
                    admin_client.post(URL, payload(), format="json").status_code == 201
                )
            assert admin_client.post(URL, payload(), format="json").status_code == 429

    def test_key_is_scoped_to_user_and_org(self, admin_client, user_client):
        data = payload()
        assert admin_client.post(URL, data, format="json").status_code == 201
        assert user_client.post(URL, data, format="json").status_code == 201
        assert len(mail.outbox) == 2

    def test_help_needs_only_a_question_and_does_not_repeat_subject(self, user_client):
        data = payload()
        data.pop("subject")
        data.pop("tried")
        data["question"] = "How do I\nadd a team?"
        response = user_client.post(URL, data, format="json")
        assert response.status_code == 201, response.data
        assert mail.outbox[0].subject.endswith("How do I add a team?")

    def test_bug_can_be_reported_without_reproduction_steps(self, user_client):
        data = payload("bug")
        data.pop("steps")
        data["record_link"] = "https://crm.example.com/contacts/123"
        response = user_client.post(URL, data, format="json")
        assert response.status_code == 201, response.data
        assert "Can continue with a workaround" in mail.outbox[0].body
        assert "Sometimes" in mail.outbox[0].body
        assert data["record_link"] in mail.outbox[0].body

    def test_feature_needs_an_outcome_but_not_a_solution(self, user_client):
        data = payload("feature")
        data.pop("suggestion")
        data["audience"] = "team"
        response = user_client.post(URL, data, format="json")
        assert response.status_code == 201, response.data
        assert "Their team" in mail.outbox[0].body

    @pytest.mark.parametrize(
        "field,value",
        [
            ("impact", "urgent"),
            ("frequency", "bad"),
            ("record_link", "javascript:alert(1)"),
        ],
    )
    def test_invalid_bug_context_is_rejected(self, user_client, field, value):
        data = payload("bug")
        data[field] = value
        response = user_client.post(URL, data, format="json")
        assert response.status_code == 400
        assert field in response.data
        assert len(mail.outbox) == 0
