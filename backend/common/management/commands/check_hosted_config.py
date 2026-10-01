"""Fail closed when a hosted CRM is configured like local development."""

from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


def validate_settings(config):
    errors = []
    if config.ENV_TYPE != "prod" or config.DEBUG:
        errors.append("Set ENV_TYPE=prod and DEBUG=False.")
    if len(config.SECRET_KEY.encode()) < 50 or config.SECRET_KEY.startswith(
        "django-insecure"
    ):
        errors.append(
            "Use a private, randomly generated SECRET_KEY of at least 50 bytes."
        )
    if not config.ALLOWED_HOSTS or any("*" in host for host in config.ALLOWED_HOSTS):
        errors.append("ALLOWED_HOSTS must list the specific API hostnames.")
    if getattr(config, "CORS_ORIGIN_ALLOW_ALL", False) or getattr(
        config, "CORS_ALLOW_ALL_ORIGINS", False
    ):
        errors.append("Disable unrestricted CORS.")
    if config.PASSWORD_REGISTRATION_ENABLED:
        errors.append(
            "Set PASSWORD_REGISTRATION_ENABLED=false for invite-only staging."
        )
    if urlsplit(config.FRONTEND_URL).scheme != "https":
        errors.append("FRONTEND_URL must use HTTPS.")
    if not config.SESSION_COOKIE_SECURE or not config.CSRF_COOKIE_SECURE:
        errors.append("Session and CSRF cookies must require HTTPS.")
    cache = getattr(config, "CACHES", {}).get("default", {})
    if cache.get(
        "BACKEND"
    ) != "django.core.cache.backends.redis.RedisCache" or urlsplit(
        str(cache.get("LOCATION", ""))
    ).scheme not in ("redis", "rediss"):
        errors.append(
            "Set CACHE_URL to a shared Redis URL for hosted throttles and caches."
        )
    backend = config.EMAIL_BACKEND
    if backend == "common.gmail_backend.GmailEmailBackend":
        for name in (
            "GMAIL_SYSTEM_CLIENT_ID",
            "GMAIL_SYSTEM_CLIENT_SECRET",
            "GMAIL_SYSTEM_REFRESH_TOKEN",
            "GMAIL_SYSTEM_SENDER",
        ):
            if not getattr(config, name, "").strip():
                errors.append(f"Set {name} in the private mail environment group.")
    elif backend in (
        "django.core.mail.backends.console.EmailBackend",
        "django.core.mail.backends.locmem.EmailBackend",
        "django.core.mail.backends.dummy.EmailBackend",
    ):
        errors.append("Configure a real email delivery backend.")
    if errors:
        raise CommandError("Hosted configuration is incomplete:\n" + "\n".join(errors))


class Command(BaseCommand):
    help = (
        "Validate hosted settings and verify that the database role cannot bypass RLS."
    )

    def handle(self, *args, **options):
        validate_settings(settings)
        if connection.vendor != "postgresql":
            raise CommandError("Hosted CRM requires PostgreSQL.")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
            )
            role = cursor.fetchone()
            if not role or any(role):
                raise CommandError(
                    "The database role must be NOSUPERUSER and NOBYPASSRLS."
                )
            cursor.execute("SHOW row_security")
            if cursor.fetchone()[0] != "on":
                raise CommandError("PostgreSQL row_security must be on.")
        self.stdout.write(
            self.style.SUCCESS("Hosted settings and database role checks passed.")
        )
