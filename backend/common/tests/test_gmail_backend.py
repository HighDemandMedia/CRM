import base64
from email import policy
from email.parser import BytesParser
from unittest.mock import patch

import pytest
import requests
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from google.auth.exceptions import RefreshError

from common.gmail_backend import GmailDeliveryError, GmailEmailBackend


@pytest.fixture
def gmail(settings):
    settings.GMAIL_SYSTEM_CLIENT_ID = "test-client"
    settings.GMAIL_SYSTEM_CLIENT_SECRET = "test-secret"
    settings.GMAIL_SYSTEM_REFRESH_TOKEN = "test-refresh"
    settings.GMAIL_SYSTEM_SENDER = "info@example.com"
    with (
        patch("common.gmail_backend.Credentials") as credentials,
        patch("common.gmail_backend.requests.Session") as session,
    ):
        credentials.return_value.valid = False
        credentials.return_value.token = "test-access"
        http = session.return_value.__enter__.return_value
        http.post.return_value.status_code = 200
        yield credentials.return_value, http


def message():
    msg = EmailMultiAlternatives(
        "Invitation",
        "Welcome",
        "CRM <info@example.com>",
        ["user@example.com"],
        bcc=["audit@example.com"],
        cc=["team@example.com"],
        reply_to=["support@example.com"],
    )
    msg.attach_alternative("<p>Welcome</p>", "text/html")
    msg.attach("test.txt", b"attachment", "text/plain")
    return msg


def test_send_preserves_mime_recipients_and_attachments(gmail):
    credentials, http = gmail
    assert GmailEmailBackend().send_messages([message()]) == 1
    credentials.refresh.assert_called_once()
    params = http.post.call_args.kwargs
    mime = BytesParser(policy=policy.default).parsebytes(
        base64.urlsafe_b64decode(params["json"]["raw"])
    )
    assert str(mime["To"]) == "user@example.com"
    assert str(mime["Cc"]) == "team@example.com"
    assert str(mime["Bcc"]) == "audit@example.com"
    assert str(mime["Reply-To"]) == "support@example.com"
    assert (
        mime.get_body(preferencelist=("html",)).get_content().strip()
        == "<p>Welcome</p>"
    )
    assert next(mime.iter_attachments()).get_filename() == "test.txt"
    assert params["timeout"] == 30
    assert params["allow_redirects"] is False


def test_mismatched_from_never_sends(gmail):
    _, http = gmail
    msg = message()
    msg.extra_headers = {"From": "spoof@example.com"}
    with pytest.raises(GmailDeliveryError, match="From address"):
        GmailEmailBackend().send_messages([msg])
    http.post.assert_not_called()


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_http_failure_is_not_reported_as_sent_or_retried(gmail, status):
    _, http = gmail
    http.post.return_value.status_code = status
    assert GmailEmailBackend(fail_silently=True).send_messages([message()]) == 0
    assert http.post.call_count == 1


@pytest.mark.parametrize(
    "exception", [RefreshError("secret-response"), requests.Timeout("secret-response")]
)
def test_errors_do_not_expose_credentials(gmail, exception):
    credentials, _ = gmail
    credentials.refresh.side_effect = exception
    with pytest.raises(GmailDeliveryError) as error:
        GmailEmailBackend().send_messages([message()])
    assert "secret-response" not in str(error.value)
    assert error.value.__suppress_context__


def test_no_recipients_do_not_call_google(gmail):
    credentials, http = gmail
    msg = message()
    msg.to = msg.cc = msg.bcc = []
    assert GmailEmailBackend().send_messages([msg]) == 0
    credentials.refresh.assert_not_called()
    http.post.assert_not_called()


def test_missing_settings_fail_clearly(settings):
    settings.GMAIL_SYSTEM_REFRESH_TOKEN = ""
    with pytest.raises(ImproperlyConfigured):
        GmailEmailBackend()
