from django.core.exceptions import ValidationError as ModelValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    # Mixed business/auxiliary routes can receive a valid-looking ID of the
    # wrong kind. UUID field conversion must yield a client error, never a 500.
    if isinstance(exc, ModelValidationError):
        exc = ValidationError({"detail": "Invalid field value or record identifier."})
    return drf_exception_handler(exc, context)
