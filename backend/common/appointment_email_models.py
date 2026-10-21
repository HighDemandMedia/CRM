"""Durable, tenant-scoped delivery receipts for appointment notices."""

import uuid

from django.db import models
from django.utils import timezone


class AppointmentEmailDelivery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey("common.Org", on_delete=models.CASCADE)
    appointment = models.ForeignKey("common.SalesAppointment", on_delete=models.CASCADE)
    revision = models.PositiveIntegerField()
    action = models.CharField(
        max_length=16,
        choices=[
            ("scheduled", "Scheduled"),
            ("rescheduled", "Rescheduled"),
            ("cancelled", "Cancelled"),
        ],
    )
    email = models.EmailField()
    profile = models.ForeignKey(
        "common.Profile", null=True, blank=True, on_delete=models.CASCADE
    )
    contact = models.ForeignKey(
        "contacts.Contact", null=True, blank=True, on_delete=models.CASCADE
    )
    # Only public appointment details. Never store internal_notes or attendee lists.
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    attempts = models.PositiveIntegerField(default=0)
    claim_id = models.UUIDField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "appointment_email_delivery"
        constraints = [
            models.UniqueConstraint(
                fields=["appointment", "revision", "email"],
                name="appointment_email_once",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(profile__isnull=False, contact__isnull=True)
                    | models.Q(profile__isnull=True, contact__isnull=False)
                ),
                name="appointment_email_recipient",
            ),
        ]
        indexes = [
            models.Index(
                fields=["org", "completed_at", "next_attempt_at"],
                name="appt_email_pending",
            )
        ]
