"""Exercise the installed SES backend without contacting AWS or sending mail."""

from email import policy
from email.parser import BytesParser
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError
from django.core.mail import EmailMultiAlternatives, get_connection


@pytest.fixture
def ses(settings):
    settings.EMAIL_BACKEND = "django_ses.SESBackend"
    settings.AWS_ACCESS_KEY_ID = "storage-key"
    settings.AWS_SECRET_ACCESS_KEY = "storage-secret"
    settings.AWS_SES_ACCESS_KEY_ID = "mail-key"
    settings.AWS_SES_SECRET_ACCESS_KEY = "mail-secret"
    settings.AWS_SES_REGION_NAME = "us-east-1"
    settings.AWS_SES_REGION_ENDPOINT = "email.us-east-1.amazonaws.com"
    settings.AWS_SES_AUTO_THROTTLE = 0
    settings.AWS_SES_CONFIGURATION_SET = None
    with patch("django_ses.boto3.Session") as session:
        client = session.return_value.client.return_value
        client.send_raw_email.return_value = {
            "MessageId": "test-message",
            "ResponseMetadata": {"RequestId": "test-request"},
        }
        yield session, client


def message():
    mail = EmailMultiAlternatives(
        "HDM CRM invitation",
        "Welcome",
        "HDM CRM <info@example.com>",
        ["recipient@example.com"],
        cc=["team@example.com"],
        bcc=["private@example.com"],
        reply_to=["support@example.com"],
    )
    mail.attach_alternative("<p>Welcome to HDM CRM</p>", "text/html")
    mail.attach("event.ics", b"BEGIN:VCALENDAR\r\nEND:VCALENDAR", "text/calendar")
    return mail


def test_ses_uses_mail_credentials_and_preserves_message(ses):
    session, client = ses
    assert get_connection().send_messages([message()]) == 1
    session.assert_called_once_with(
        aws_access_key_id="mail-key",
        aws_secret_access_key="mail-secret",
        aws_session_token=None,
    )
    assert session.return_value.client.call_args.kwargs["region_name"] == "us-east-1"
    payload = client.send_raw_email.call_args.kwargs
    assert payload["Source"] == "HDM CRM <info@example.com>"
    assert set(payload["Destinations"]) == {
        "recipient@example.com",
        "team@example.com",
        "private@example.com",
    }
    mime = BytesParser(policy=policy.default).parsebytes(payload["RawMessage"]["Data"])
    assert mime["Reply-To"] == "support@example.com"
    assert mime["Bcc"] is None
    assert mime.get_body(preferencelist=("html",)).get_content().strip() == (
        "<p>Welcome to HDM CRM</p>"
    )
    assert next(mime.iter_attachments()).get_filename() == "event.ics"


def test_ses_failure_does_not_fall_back_to_google(ses):
    _, client = ses
    client.send_raw_email.side_effect = ClientError(
        {"Error": {"Code": "MessageRejected", "Message": "Test rejection"}},
        "SendRawEmail",
    )
    with patch(
        "common.gmail_backend.GmailEmailBackend.send_messages", new=Mock()
    ) as gmail:
        with pytest.raises(ClientError):
            get_connection().send_messages([message()])
        gmail.assert_not_called()
    client.send_raw_email.assert_called_once()
