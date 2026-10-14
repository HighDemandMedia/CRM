import uuid

from django.conf import settings
from django.db import models


class LegalAcceptance(models.Model):
    """Account-level receipt, like invitations; no public CRUD or tenant listing."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    org = models.ForeignKey("common.Org", on_delete=models.CASCADE)
    version = models.CharField(max_length=40)
    locale = models.CharField(
        max_length=2, choices=[("en", "English"), ("es", "Español")]
    )
    on_behalf_of_organization = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(auto_now_add=True)
