from django.core.exceptions import ValidationError as ModelValidationError
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    if isinstance(exc, IntegrityError):
        cause = exc.__cause__
        constraint = getattr(getattr(cause, "diag", None), "constraint_name", None)
        conflicts = {
            "unique_contact_email_per_org": (
                "email",
                "Contact already exists with this email.",
            ),
            "unique_contact_phone_per_org": (
                "phone",
                "Contact already exists with this phone number.",
            ),
            "unique_account_domain_per_org": (
                "website",
                "Company already exists with this domain.",
            ),
        }
        if constraint in conflicts:
            field, message = conflicts[constraint]
            exc = ValidationError({"errors": {field: [message]}})
    # Mixed business/auxiliary routes can receive a valid-looking ID of the
    # wrong kind. UUID field conversion must yield a client error, never a 500.
    if isinstance(exc, ModelValidationError):
        exc = ValidationError({"detail": "Invalid field value or record identifier."})
    return drf_exception_handler(exc, context)
