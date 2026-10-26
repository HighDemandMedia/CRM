"""Shared validation for the editable fields in CRM record forms."""

import re
import unicodedata

from rest_framework.exceptions import ValidationError

from common.phone_numbers import PHONE_ERROR, phone_e164

CALENDAR_TARGETS = {"Contact", "Account"}


def clean_record_values(data, target):
    if not hasattr(data, "get"):
        return data
    data = data.copy()
    errors = {}
    if target in CALENDAR_TARGETS and "appointment_at" in data:
        errors["appointment_at"] = (
            "Schedule, reschedule or cancel appointments in Calendar."
        )
    labels = {
        "city": "City",
        "state": "State / region",
        "address_line": "Address",
        "postcode": "Postal code",
        "name": "Name",
        "title": "Title",
        "first_name": "Name",
        "last_name": "Last name",
        "phone": "Phone",
    }
    for key, label in labels.items():
        value = data.get(key)
        if value is not None and not isinstance(value, str):
            errors[key] = f"{label} must be text."
            continue
        if not isinstance(value, str):
            continue
        value = unicodedata.normalize("NFC", value).strip()
        if any(unicodedata.category(char) == "Cc" for char in value):
            errors[key] = f"{label} must be a single line without control characters."
            continue
        value = re.sub(r"\s+", " ", value)
        data[key] = value
        if not value:
            continue
        if key in ("city", "state") and (
            not any(char.isalpha() for char in value)
            or any(
                not (
                    unicodedata.category(char)[0] in "LMN" or char in " .,'’‘-‐‑–—()/&"
                )
                for char in value
            )
        ):
            errors[key] = f"Enter a valid {label.lower()} name."
        elif key == "postcode" and (
            not any(char.isalnum() for char in value)
            or any(not (char.isalnum() or char in " -") for char in value)
        ):
            errors[key] = "Use letters, numbers, spaces or hyphens for the postal code."
        elif key == "phone":
            try:
                data[key] = phone_e164(value)
            except ValueError:
                errors[key] = PHONE_ERROR
    if errors:
        raise ValidationError(errors)
    return data
