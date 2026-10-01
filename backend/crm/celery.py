from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.dev_settings')
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.server_settings')

app = Celery("crm")

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Historical Django models remain installed for migrations; only active workflows load jobs.
app.autodiscover_tasks(
    ["common", "accounts", "contacts", "opportunity", "webforms", "cases"]
)
app.autodiscover_tasks(
    ["tasks"], related_name="celery_tasks"
)  # tasks app uses celery_tasks.py

# Celery Beat Schedule for recurring tasks
app.conf.beat_schedule = {
    "purge-deleted-attachment-files": {
        "task": "common.tasks.purge_deleted_attachment_files",
        "schedule": crontab(minute="*/5"),
    },
    "send-due-reminders": {
        "task": "common.tasks.send_due_reminders",
        "schedule": crontab(minute="*"),
        "options": {"expires": 60},
    },
    "retry-webform-emails": {
        "task": "webforms.tasks.retry_pending_webform_emails",
        "schedule": crontab(minute="*/5"),
    },
    "sync-personal-google-accounts": {
        "task": "common.tasks.schedule_google_sync",
        "schedule": crontab(minute="*/5"),
    },
    # Check for stale/rotten opportunities - daily at 8 AM
    "check-stale-opportunities": {
        "task": "opportunity.tasks.check_stale_opportunities",
        "schedule": crontab(hour=8, minute=0),
    },
    # Purge already-read in-app notifications older than 90 days - daily at 3 AM
    "purge-read-notifications": {
        "task": "common.tasks.purge_read_notifications",
        "schedule": crontab(hour=3, minute=0),
    },
    # Drop rotated/expired refresh token records - daily at 3:30 AM
    "flush-expired-refresh-tokens": {
        "task": "common.tasks.flush_expired_refresh_tokens",
        "schedule": crontab(hour=3, minute=30),
    },
}
