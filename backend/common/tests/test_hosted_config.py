from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.core.management.base import CommandError

from common.management.commands.check_hosted_config import Command, validate_settings


@pytest.fixture
def config():
    return SimpleNamespace(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.redis.RedisCache",
                "LOCATION": "redis://redis:6379/1",
            }
        },
        ENV_TYPE="prod",
        DEBUG=False,
        SECRET_KEY="random-test-key-" * 5,
        ALLOWED_HOSTS=["api.example.com"],
        CORS_ORIGIN_ALLOW_ALL=False,
        PASSWORD_REGISTRATION_ENABLED=False,
        FRONTEND_URL="https://crm.example.com",
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        EMAIL_BACKEND="common.gmail_backend.GmailEmailBackend",
        GMAIL_SYSTEM_CLIENT_ID="test",
        GMAIL_SYSTEM_CLIENT_SECRET="test",
        GMAIL_SYSTEM_REFRESH_TOKEN="test",
        GMAIL_SYSTEM_SENDER="info@example.com",
    )


@pytest.mark.parametrize(
    "name,value",
    [
        ("CACHES", {}),
        ("ENV_TYPE", "dev"),
        ("DEBUG", True),
        ("SECRET_KEY", "short"),
        ("ALLOWED_HOSTS", ["*"]),
        ("CORS_ORIGIN_ALLOW_ALL", True),
        ("PASSWORD_REGISTRATION_ENABLED", True),
        ("FRONTEND_URL", "http://crm.example.com"),
        ("SESSION_COOKIE_SECURE", False),
        ("GMAIL_SYSTEM_REFRESH_TOKEN", ""),
        ("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"),
    ],
)
def test_insecure_hosted_settings_rejected(config, name, value):
    setattr(config, name, value)
    with pytest.raises(CommandError):
        validate_settings(config)


@pytest.fixture
def ses_config(config):
    config.EMAIL_BACKEND = "django_ses.SESBackend"
    config.AWS_SES_REGION_NAME = "us-east-1"
    config.DEFAULT_FROM_EMAIL = "HDM CRM <info@example.com>"
    return config


def test_ses_allows_existing_credential_chain(ses_config):
    validate_settings(ses_config)


def test_ses_allows_dedicated_credentials(ses_config):
    ses_config.AWS_SES_ACCESS_KEY_ID = "ses-test-key"
    ses_config.AWS_SES_SECRET_ACCESS_KEY = "ses-test-secret"
    validate_settings(ses_config)


@pytest.mark.parametrize(
    "name,value",
    [
        ("AWS_SES_REGION_NAME", ""),
        ("DEFAULT_FROM_EMAIL", "noreply@localhost"),
        ("AWS_SES_ACCESS_KEY_ID", "only-key"),
        ("AWS_SES_SECRET_ACCESS_KEY", "only-secret"),
    ],
)
def test_ses_rejects_incomplete_configuration(ses_config, name, value):
    setattr(ses_config, name, value)
    with pytest.raises(CommandError):
        validate_settings(ses_config)


@pytest.mark.parametrize(
    "role,row_security,allowed",
    [
        ((False, False), "on", True),
        ((True, False), "on", False),
        ((False, True), "on", False),
        ((False, False), "off", False),
    ],
)
def test_database_role_cannot_bypass_isolation(config, role, row_security, allowed):
    connection = MagicMock(vendor="postgresql")
    connection.cursor.return_value.__enter__.return_value.fetchone.side_effect = [
        role,
        (row_security,),
    ]
    with (
        patch("common.management.commands.check_hosted_config.settings", config),
        patch("common.management.commands.check_hosted_config.connection", connection),
    ):
        if allowed:
            Command().handle()
        else:
            with pytest.raises(CommandError):
                Command().handle()
