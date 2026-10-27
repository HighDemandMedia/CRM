"""Accept compact business IDs and UUIDs used by auxiliary CRM records."""

from common.identifiers import resolve_identifier


class UUIDLikeConverter:
    regex = "[^/]+"

    def to_python(self, value):
        try:
            return resolve_identifier(value)
        except (AttributeError, TypeError, ValueError):
            raise ValueError("Invalid record identifier") from None

    def to_url(self, value):
        return str(value)
