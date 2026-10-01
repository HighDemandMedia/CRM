"""Provision an isolated local customer demo without changing existing tenants."""

from uuid import NAMESPACE_URL, uuid5

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from common.models import Org, Profile, User


class Command(BaseCommand):
    help = "Create an isolated local customer demo with fictional data. Repeated runs preserve edits."

    def add_arguments(self, parser):
        parser.add_argument("--owner-email", default="admin@example.com")
        parser.add_argument("--demo-email", default="demo@example.com")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Customer demo setup is available only in local DEBUG mode."
            )
        email = options["demo_email"].strip().lower()
        owner = User.objects.filter(
            email__iexact=options["owner_email"], is_active=True
        ).first()
        if not owner or owner.email.lower() == email:
            raise CommandError(
                "An existing active owner and a separate demo email are required."
            )
        org_id = uuid5(NAMESPACE_URL, f"hdm-customer-demo:{email}")
        user = User.objects.filter(email__iexact=email).first()
        if user and (
            not Profile.objects.filter(user=user, org_id=org_id, is_demo=True).exists()
            or Profile.objects.filter(user=user).exclude(org_id=org_id).exists()
            or user.is_staff
            or user.is_superuser
        ):
            raise CommandError(
                "That email is already used outside this demo. Choose a new demo email."
            )
        org, created = Org.objects.get_or_create(
            pk=org_id,
            defaults={
                "name": "High Demand Media · Demo",
                "owner": owner,
                "timezone": "America/New_York",
                "default_currency": "USD",
            },
        )
        if org.owner_id != owner.pk:
            raise CommandError("This demo belongs to a different owner.")
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('app.current_org', %s, true)", [str(org.pk)]
                )
        if not user:
            user = User(email=email, name="Customer Demo", is_active=True)
            user.set_unusable_password()
            user.save()
        Profile.objects.get_or_create(
            org=org, user=owner, defaults={"role": "ADMIN", "is_active": True}
        )
        demo, _ = Profile.objects.get_or_create(
            org=org,
            user=user,
            defaults={
                "role": "ADMIN",
                "is_demo": True,
                "is_active": True,
                "has_sales_access": True,
                "language": "English",
            },
        )
        # Administrator rights belong only to this organization's membership.
        demo.role = "ADMIN"
        demo.access_role = None
        demo.save()
        if created:
            call_command(
                "seed_today_demo", org=str(org.pk), email=email, stdout=self.stdout
            )
        self.stdout.write(
            self.style.SUCCESS(f"Demo ready: {org.name} | {email} | {org.pk}")
        )
