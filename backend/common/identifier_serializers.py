from rest_framework import serializers

from common.identifiers import normalize_identifier


class IdentifierField(serializers.CharField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            return normalize_identifier(value)
        except (TypeError, ValueError, AttributeError):
            self.fail("invalid")
