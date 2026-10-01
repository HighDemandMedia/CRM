"""Create or refresh only this command's clearly labelled local demo records."""

from datetime import datetime, time, timedelta
from unittest.mock import patch
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from accounts.models import Account
from cases.models import Case
from common.models import Comment, Org, Profile, SalesAppointment
from contacts.models import Contact
from opportunity.models import Opportunity
from tasks.models import Task


class Command(BaseCommand):
    help = "Create labelled Today demo data, without deleting existing records or sending email."

    def add_arguments(self, parser):
        parser.add_argument("--org", required=True)
        parser.add_argument("--email", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        org = Org.objects.get(pk=options["org"])
        profile = (
            Profile.objects.filter(
                org=org, user__email=options["email"], is_active=True
            )
            .select_related("user")
            .first()
        )
        if not profile:
            raise CommandError("An active user in this organization is required.")
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('app.current_org', %s, true)", [str(org.pk)]
                )
        with (
            timezone.override(ZoneInfo(org.timezone)),
            patch("cases.tasks.notify_portal_contacts.delay"),
            patch("cases.tasks.send_email_to_assigned_user.delay"),
        ):
            today = timezone.localdate()

            def at(day, hour, minute=0):
                return timezone.make_aware(
                    datetime.combine(today + timedelta(days=day), time(hour, minute))
                )

            def identity(key):
                return uuid5(NAMESPACE_URL, f"hdm-today-demo:{org.pk}:{key}")

            def make(model, key, **fields):
                fields.update(org=org, created_by=profile.user)
                if any(field.name == "is_sample" for field in model._meta.fields):
                    fields["is_sample"] = True
                obj, _ = model.objects.update_or_create(
                    pk=identity(key), defaults=fields
                )
                if hasattr(obj, "assigned_to"):
                    obj.assigned_to.set([profile])
                return obj

            companies = [
                make(
                    Account,
                    f"company-{i}",
                    name=name,
                    website=f"https://demo-{i}.example.com",
                    email=f"company-{i}@example.com",
                    phone=f"+1202555010{i}",
                    source="GOOGLE",
                    stage="QUALIFIED",
                    language="English",
                )
                for i, name in enumerate(
                    ["Demo · Cedar Home Services", "Demo · Harbor Studio"]
                )
            ]
            contacts = [
                make(
                    Contact,
                    f"contact-{i}",
                    first_name="Demo",
                    last_name=name,
                    email=f"today-contact-{i}@example.com",
                    phone=f"+1202555011{i}",
                    source="META",
                    stage="QUALIFIED" if i == 0 else "FOLLOW_UP",
                    language="Spanish" if i == 1 else "English",
                )
                for i, name in enumerate(
                    ["Alex Morgan", "Sofia Rivera", "Jamie Parker"]
                )
            ]
            for i, contact in enumerate(contacts):
                companies[i % 2].contacts.add(contact)
            deals = []
            for i, (name, stage, days, amount) in enumerate(
                [
                    ("Website proposal", "PROPOSAL", 0, 4200),
                    ("Campaign renewal", "QUALIFICATION", -2, 2800),
                    ("Landing page project", "PROSPECTING", 0, 1600),
                    ("Brand refresh", "NEGOTIATION", 3, 6500),
                    ("Completed launch", "CLOSED_WON", -1, 3200),
                    ("Paused campaign", "CLOSED_LOST", -3, 1800),
                ]
            ):
                deal = make(
                    Opportunity,
                    f"deal-{i}",
                    name=f"Demo · {name}",
                    stage=stage,
                    closed_on=today + timedelta(days=days),
                    amount=amount,
                    currency="USD",
                    priority="HIGH" if days < 0 else "MEDIUM",
                    lead_source="META",
                    language="English",
                    account=companies[i % 2],
                )
                deal.contacts.set([contacts[i % 3]])
                deals.append(deal)
            tickets = []
            for i, (name, status, days, priority) in enumerate(
                [
                    ("Review website access", "New", 0, "High"),
                    ("Resolve tracking issue", "Assigned", -1, "High"),
                    ("Confirm billing details", "Pending", 0, "Normal"),
                    ("Launch verified", "Resolved", -1, "Normal"),
                ]
            ):
                ticket = make(
                    Case,
                    f"ticket-{i}",
                    name=f"Demo · {name}",
                    status=status,
                    priority=priority,
                    due_at=at(days, 17),
                    category="Support",
                    source="Internal",
                    description="Fictional demo ticket for the Today summary.",
                    account=companies[i % 2],
                    resolution_note="Demo verification completed."
                    if status == "Resolved"
                    else "",
                )
                ticket.contacts.set([contacts[i % 3]])
                tickets.append(ticket)
            tasks = []
            for i, (name, status, days) in enumerate(
                [
                    ("Send proposal to Alex", "New", 0),
                    ("Prepare campaign report", "In Progress", 0),
                    ("Follow up on tracking issue", "New", -1),
                    ("Confirm design feedback", "New", -2),
                    ("Plan next week campaign", "New", 3),
                    ("Send kickoff checklist", "Completed", 0),
                ]
            ):
                tasks.append(
                    make(
                        Task,
                        f"task-{i}",
                        title=f"Demo · {name}",
                        status=status,
                        priority="High" if days < 0 else "Medium",
                        due_date=today + timedelta(days=days),
                        description="Demo task. Review details, add a note, or mark it complete.",
                        account=companies[i % 2],
                    )
                )
            for i, (title, hour, minute) in enumerate(
                [
                    ("Discovery call with Alex", 9, 30),
                    ("Campaign review with Sofia", 11, 0),
                    ("Cedar project planning", 14, 0),
                    ("Harbor creative review", 16, 0),
                ]
            ):
                attendee = contacts[i] if i < 2 else companies[i - 2]
                event = make(
                    SalesAppointment,
                    f"event-{i}",
                    title=f"Demo · {title}",
                    host=profile,
                    starts_at=at(0, hour, minute),
                    ends_at=at(0, hour, minute) + timedelta(minutes=45),
                    contact=attendee if i < 2 else None,
                    company=attendee if i >= 2 else None,
                    deal=deals[i],
                    internal_notes="Demo meeting: review objectives and agree on next steps.",
                    cancelled_at=None,
                    cancelled_by=None,
                )
                type(attendee).objects.filter(pk=attendee.pk).update(
                    appointment_at=event.starts_at
                )
            for obj in [*contacts, *companies, *deals, *tasks]:
                Comment.objects.update_or_create(
                    pk=identity(f"note-{obj.pk}"),
                    defaults={
                        "org": org,
                        "content_type": ContentType.objects.get_for_model(obj),
                        "object_id": obj.pk,
                        "comment": "Demo note: initial details reviewed. Ready for the next action.",
                        "commented_by": profile,
                        "is_internal": True,
                    },
                )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Today demo ready in {org.name}: 3 contacts, 2 companies, 6 deals, 4 tickets, 6 tasks, 4 events for {today}."
                )
            )
