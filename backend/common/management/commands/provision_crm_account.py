"""Private provisioning for the platform owner or an independent customer tenant."""

import warnings
from getpass import GetPassWarning, getpass

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from rest_framework.exceptions import ValidationError

from common.models import Org, Profile, User
from common.rbac import ensure_default_roles
from common.serializer import OrgProfileCreateSerializer
from common.views.password_auth_views import RegisterInput


class Command(BaseCommand):
    help = "Privately create a CRM account and its organization; password is prompted securely."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--organization", required=True)
        parser.add_argument("--name")
        parser.add_argument("--timezone", default="America/New_York")
        parser.add_argument("--platform-owner", action="store_true")

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        name = (options["name"] or input("Full name: ")).strip()
        organization = options["organization"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError("User already exists. No existing account was changed.")
        if Org.objects.filter(name__iexact=organization).exists():
            raise CommandError(
                "Organization already exists. No existing organization was changed."
            )
        if (
            options["platform_owner"]
            and User.objects.filter(is_superuser=True).exists()
        ):
            raise CommandError(
                "A platform owner already exists. This command cannot appoint another."
            )
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", GetPassWarning)
                password = getpass("Password (at least 10 characters): ")
                confirmation = getpass("Repeat password: ")
        except (GetPassWarning, EOFError) as exc:
            raise CommandError(
                "Use an interactive Shell with hidden password input."
            ) from exc
        if password != confirmation:
            raise CommandError("Passwords do not match. Nothing was created.")
        try:
            data = RegisterInput(
                data={
                    "email": email,
                    "name": name,
                    "password": password,
                    "organization": organization,
                    "timezone": options["timezone"],
                }
            )
            data.is_valid(raise_exception=True)
            with transaction.atomic():
                # Serialize CLI provisioning, including competing owner creation.
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT pg_advisory_xact_lock(84291367)")
                if (
                    options["platform_owner"]
                    and User.objects.filter(is_superuser=True).exists()
                ):
                    raise CommandError("A platform owner already exists.")
                org_data = OrgProfileCreateSerializer(
                    data={
                        "name": organization,
                        "timezone": options["timezone"],
                    }
                )
                org_data.is_valid(raise_exception=True)
                user = User.objects.create_user(
                    email,
                    password,
                    name=name,
                    is_superuser=options["platform_owner"],
                    is_staff=options["platform_owner"],
                )
                org = org_data.save(created_by=user)
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT set_config('app.current_org', %s, true)",
                            [str(org.pk)],
                        )
                ensure_default_roles(org)
                Profile.objects.create(user=user, org=org, role="ADMIN", is_active=True)
        except ValidationError as exc:
            raise CommandError(str(exc.detail)) from exc
        label = (
            "Platform owner"
            if options["platform_owner"]
            else "Organization Super Admin"
        )
        self.stdout.write(
            self.style.SUCCESS(f"Created {email} — {organization} — {label}.")
        )
