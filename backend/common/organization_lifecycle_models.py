"""Minimal deletion ledger. Identifiers deliberately survive tenant deletion."""

from django.db import models


class OrganizationClosure(models.Model):
    org_id = models.CharField(max_length=36, primary_key=True)
    requested_at = models.DateTimeField()
    deletion_due_at = models.DateTimeField(db_index=True)
    reactivated_at = models.DateTimeField(null=True, blank=True)
    data_deleted_at = models.DateTimeField(null=True, blank=True)
    files_deleted_at = models.DateTimeField(null=True, blank=True)


class OrganizationLifecycleEvent(models.Model):
    org_id = models.CharField(max_length=36, db_index=True)
    actor_id = models.CharField(max_length=36, null=True, blank=True)
    action = models.CharField(max_length=16)
    occurred_at = models.DateTimeField(auto_now_add=True)
