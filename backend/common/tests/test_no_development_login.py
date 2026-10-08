"""Local tooling must not provide an alternate way to authenticate a user."""

from collections import Counter
from io import StringIO

import pytest
from django.core.management import call_command, get_commands
from django.core.management.base import CommandError

from common.management.commands.seed_data import Command as SeedCommand
from common.models import MagicLinkToken, User

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("command", ["devlogin", "local_login_link"])
@pytest.mark.parametrize("debug", [True, False])
def test_login_shortcuts_are_unavailable_even_with_development_opt_in(
    command, debug, settings, monkeypatch
):
    settings.DEBUG = debug
    settings.FRONTEND_URL = "http://localhost:5173"
    monkeypatch.setenv("CRM_LOCAL_LOGIN", "1")
    user = User.objects.create_user(email="local@example.com")
    get_commands.cache_clear()
    assert command not in get_commands()
    with pytest.raises(CommandError, match="Unknown command"):
        call_command(command, stdout=StringIO())
    assert not MagicLinkToken.objects.exists()
    user.refresh_from_db()
    assert user.last_login is None
    assert User.objects.count() == 1


@pytest.mark.parametrize(
    "email,password",
    [(None, None), ("owner@example.com", ""), ("", "Explicit-bootstrap-932!")],
)
def test_bootstrap_without_explicit_credentials_does_not_create_an_account(
    email, password, monkeypatch
):
    for key, value in [("ADMIN_EMAIL", email), ("ADMIN_PASSWORD", password)]:
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    output = StringIO()
    call_command("create_default_admin", stdout=output)
    assert "Skipping superuser bootstrap" in output.getvalue()
    assert not User.objects.exists()


@pytest.mark.parametrize(
    "email,password",
    [("owner@example.com", "admin"), ("invalid", "Explicit-bootstrap-932!")],
)
def test_bootstrap_rejects_invalid_credentials(email, password, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", email)
    monkeypatch.setenv("ADMIN_PASSWORD", password)
    with pytest.raises(CommandError, match="failed validation") as exc:
        call_command("create_default_admin", stdout=StringIO())
    assert password not in str(exc.value)
    assert not User.objects.exists()


def test_explicit_bootstrap_is_idempotent_and_does_not_reset_password(monkeypatch):
    email = "owner@example.com"
    password = "Explicit-bootstrap-932!"
    monkeypatch.setenv("ADMIN_EMAIL", email)
    monkeypatch.setenv("ADMIN_PASSWORD", password)
    output = StringIO()
    call_command("create_default_admin", stdout=output)
    user = User.objects.get(email=email)
    assert user.is_staff and user.is_superuser
    assert user.check_password(password)
    assert password not in output.getvalue()
    monkeypatch.setenv("ADMIN_PASSWORD", "Another-explicit-password-942!")
    call_command("create_default_admin", stdout=StringIO())
    user.refresh_from_db()
    assert User.objects.count() == 1
    assert user.check_password(password)


def test_seeding_has_no_shared_password_and_preserves_existing_credentials(org_a):
    command = SeedCommand(stdout=StringIO())
    command.stats = Counter()
    options = vars(command.create_parser("manage.py", "seed_data").parse_args([]))
    assert options["password"] is None
    user = command.get_or_create_admin("demo@example.com", options["password"])
    assert not user.has_usable_password()
    command.admin_user = user
    profiles = command.create_profiles(org_a, 2, options["password"])
    assert len(profiles) == 3
    assert all(not profile.user.has_usable_password() for profile in profiles)
    user.set_password("Personal-password-973!")
    user.save()
    reused = command.get_or_create_admin(user.email, options["password"])
    assert reused.pk == user.pk
    assert reused.check_password("Personal-password-973!")
