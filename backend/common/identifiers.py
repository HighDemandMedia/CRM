"""Identifiers for business records; never use these for authentication tokens."""

import re
import secrets
import uuid

from django.db import models, router, transaction

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
COMPACT_ID_RE = re.compile(
    r"(?:HDM-[0-9A-HJKMNP-TV-Z]{8}|(?:USR|CON|COM|DEA|TSK|TKT|EVT)-[0-9]{4,20})\Z"
)


def normalize_identifier(value):
    text = str(value)
    if COMPACT_ID_RE.fullmatch(text):
        return text
    return str(uuid.UUID(text))


def resolve_identifier(value):
    """Keep existing links and external references valid after the migration."""
    normalized = normalize_identifier(value)
    if COMPACT_ID_RE.fullmatch(normalized):
        return normalized
    from common.models import LegacyBusinessID

    return (
        LegacyBusinessID.objects.filter(pk=normalized)
        .values_list("replacement", flat=True)
        .first()
        or normalized
    )


class BusinessIDField(models.CharField):
    """Allocate on insert, not during form previews or model construction."""

    empty_strings_allowed = False

    def __init__(self, *, prefix, **kwargs):
        self.prefix = prefix
        kwargs.setdefault("max_length", 36)
        kwargs.setdefault("primary_key", True)
        kwargs.setdefault("editable", False)
        super().__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["prefix"] = self.prefix
        return name, path, args, kwargs

    def get_db_prep_value(self, value, connection, prepared=False):
        value = super().get_db_prep_value(value, connection, prepared)
        if value and not COMPACT_ID_RE.fullmatch(str(value)):
            try:
                legacy = str(uuid.UUID(str(value)))
            except (ValueError, TypeError, AttributeError):
                return value
            from common.models import LegacyBusinessID

            # Old signed sessions and already queued jobs may still carry a UUID.
            # Resolve at the field boundary, including FKs, without changing
            # authentication claims, token entropy, or tenant authorization.
            return (
                LegacyBusinessID.objects.using(connection.alias)
                .filter(pk=legacy)
                .values_list("replacement", flat=True)
                .first()
                or value
            )
        return value

    def get_pk_value_on_save(self, instance):
        from common.models import BusinessIDSequence

        using = instance._state.db or router.db_for_write(
            type(instance), instance=instance
        )
        # One sequence per kind gives unique PKs across tenants. A database lock
        # also serializes creation from API, workers, and concurrent imports.
        with transaction.atomic(using=using):
            sequence, _ = BusinessIDSequence.objects.using(using).get_or_create(
                prefix=self.prefix
            )
            sequence = (
                BusinessIDSequence.objects.using(using)
                .select_for_update()
                .get(pk=sequence.pk)
            )
            if self.prefix == "HDM":
                # Reservations outlive deleted organizations, preventing reuse.
                from common.models import OrganizationIDReservation

                while True:
                    value = "HDM-" + "".join(secrets.choice(ALPHABET) for _ in range(8))
                    _, created = OrganizationIDReservation.objects.using(
                        using
                    ).get_or_create(pk=value)
                    if created:
                        return value
            sequence.last_number += 1
            sequence.save(using=using, update_fields=["last_number"])
            return f"{self.prefix}-{sequence.last_number:04d}"
