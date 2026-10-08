"""Personal Google connections. Every row belongs to one org and one profile."""

import uuid

from django.db import models


class GoogleConnection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey("common.Org", on_delete=models.CASCADE)
    profile = models.ForeignKey("common.Profile", on_delete=models.CASCADE)
    service = models.CharField(
        max_length=16, choices=[("gmail", "Gmail"), ("calendar", "Calendar")]
    )
    email = models.EmailField(blank=True)
    subject = models.CharField(max_length=255, blank=True)
    encrypted_refresh_token = models.TextField(blank=True)
    scopes = models.JSONField(default=list)
    calendar_id = models.CharField(max_length=1024, default="primary")
    calendar_name = models.CharField(max_length=255, default="Primary calendar")
    calendar_writable = models.BooleanField(default=False)
    history_id = models.CharField(max_length=64, blank=True)
    initial_history_id = models.CharField(max_length=64, blank=True)
    mail_page_token = models.TextField(blank=True)
    mail_contacts_fingerprint = models.CharField(max_length=64, blank=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    error = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, default="disconnected")
    oauth_state_hash = models.CharField(max_length=64, blank=True)
    encrypted_verifier = models.TextField(blank=True)
    oauth_started_at = models.DateTimeField(null=True, blank=True)
    sync_started_at = models.DateTimeField(null=True, blank=True)
    generation = models.UUIDField(default=uuid.uuid4)

    class Meta:
        db_table = "google_connection"
        constraints = [
            models.UniqueConstraint(
                fields=["org", "profile", "service"],
                name="google_profile_service_unique",
            )
        ]


class GoogleCalendarEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey("common.Org", on_delete=models.CASCADE)
    connection = models.ForeignKey(
        GoogleConnection, on_delete=models.CASCADE, related_name="events"
    )
    external_id = models.CharField(max_length=1024)
    title = models.CharField(max_length=1024)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    start_date = models.CharField(max_length=10, blank=True)
    end_date = models.CharField(max_length=10, blank=True)
    href = models.URLField(max_length=2048, blank=True)
    busy = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "google_calendar_event"
        constraints = [
            models.UniqueConstraint(
                fields=["connection", "external_id"],
                name="google_calendar_event_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=["org", "connection", "starts_at"], name="google_events_range"
            )
        ]


class GoogleMailActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey("common.Org", on_delete=models.CASCADE)
    connection = models.ForeignKey(
        GoogleConnection, on_delete=models.CASCADE, related_name="mail_activity"
    )
    message_id = models.CharField(max_length=128)
    thread_id = models.CharField(max_length=128)
    contact_email = models.EmailField()
    subject = models.CharField(max_length=1024, blank=True)
    sender = models.EmailField()
    recipients = models.JSONField(default=list)
    cc = models.JSONField(default=list)
    reply_to = models.JSONField(default=list, blank=True)
    encrypted_body = models.TextField(blank=True)
    direction = models.CharField(max_length=8)
    occurred_at = models.DateTimeField()

    class Meta:
        db_table = "google_mail_activity"
        constraints = [
            models.UniqueConstraint(
                fields=["connection", "message_id", "contact_email"],
                name="google_mail_activity_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=["org", "contact_email", "occurred_at"],
                name="google_mail_contact",
            )
        ]


class GoogleCalendarMirror(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey("common.Org", on_delete=models.CASCADE)
    connection = models.ForeignKey(
        GoogleConnection, on_delete=models.CASCADE, related_name="mirrors"
    )
    appointment = models.ForeignKey("common.SalesAppointment", on_delete=models.CASCADE)
    external_id = models.CharField(max_length=1024)
    etag = models.CharField(max_length=255, blank=True)
    fingerprint = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = "google_calendar_mirror"
        constraints = [
            models.UniqueConstraint(
                fields=["connection", "appointment"],
                name="google_mirror_appointment_unique",
            )
        ]


class GoogleMailSendOperation(models.Model):
    """Durable duplicate prevention, including ambiguous provider timeouts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(GoogleConnection, on_delete=models.CASCADE)
    request_id = models.UUIDField()
    payload_digest = models.CharField(max_length=64)
    status = models.CharField(max_length=16, default="sending")
    message_id = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["connection", "request_id"], name="google_send_request_unique"
            )
        ]
