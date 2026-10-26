"""Admin-reviewed contact merges; the secondary remains as provenance."""

from common.record_merge import RecordMergeView
from contacts.models import Contact

FIELDS = [
    "email",
    "phone",
    "language",
    "source",
    "stage",
    "preferred_communication_channel",
    "organization",
    "title",
    "department",
    "linkedin_url",
    "address_line",
    "city",
    "state",
    "postcode",
    "country",
    "account",
]


class ContactMergeView(RecordMergeView):
    model = Contact
    fields = FIELDS
    search_fields = ("first_name", "last_name", "email", "phone")
    search_order = "first_name"
    noun = "contact"
    plural = "contacts"
    salt = "contacts.merge.v1"
