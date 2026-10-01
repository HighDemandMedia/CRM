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
