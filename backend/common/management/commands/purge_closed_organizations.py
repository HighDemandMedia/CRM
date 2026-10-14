"""Inspect due closures by default; deletion requires --execute and the gate."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from common.models import OrganizationClosure, PendingFileDeletion
from common.organization_purge import finish_file_deletions, purge_organization


class Command(BaseCommand):
    help = (
        "Inspect due organization deletions; --execute requires CRM_ORG_PURGE_ENABLED."
    )

    def add_arguments(self, parser):
        parser.add_argument("--execute", action="store_true")

    def handle(self, *args, **options):
        if options["execute"] and not settings.CRM_ORG_PURGE_ENABLED:
            raise CommandError("Organization purge is disabled.")
        rows = OrganizationClosure.objects.filter(
            reactivated_at__isnull=True,
            deletion_due_at__lte=timezone.now(),
            data_deleted_at__isnull=True,
        )
        failed = 0
        for row in rows.iterator():
            if options["execute"]:
                try:
                    purge_organization(row.org_id)
                except Exception:
                    failed += 1
                    # Do not print related customer records or storage credentials.
                    self.stderr.write(
                        f"Deletion failed for {row.org_id}; inspect server logs and retry."
                    )
            else:
                self.stdout.write(f"Due: {row.org_id}")
        if options["execute"]:
            finish_file_deletions()
        self.stdout.write(
            f"Pending storage files: {PendingFileDeletion.objects.count()}"
        )
        if failed:
            raise CommandError(
                f"{failed} organization deletion(s) failed; no completion claimed."
            )
