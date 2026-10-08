import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

User = get_user_model()


class Command(BaseCommand):
    help = "Create a bootstrap superuser only with explicitly configured credentials"

    def handle(self, *args, **options):
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.SUCCESS("Superuser already exists; skipping."))
            return

        email = os.environ.get("ADMIN_EMAIL", "").strip()
        password = os.environ.get("ADMIN_PASSWORD", "")

        if not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    "Skipping superuser bootstrap: ADMIN_EMAIL and ADMIN_PASSWORD "
                    "must both be explicitly configured."
                )
            )
            return

        try:
            validate_email(email)
            validate_password(password, User(email=email))
        except ValidationError as exc:
            raise CommandError(
                "Bootstrap credentials failed validation. Use a valid email and "
                "a password that meets the configured password policy."
            ) from exc

        User.objects.create_superuser(
            email=email,
            password=password,
        )
        self.stdout.write(self.style.SUCCESS(f"Created default superuser: {email}"))
