"""Company merges use the same review, locking and preservation rules as contacts."""

from accounts.models import Account
from common.record_merge import RecordMergeView


class AccountMergeView(RecordMergeView):
    model = Account
    fields = (
        "email",
        "phone",
        "website",
        "language",
        "source",
        "stage",
        "preferred_communication_channel",
        "industry",
        "number_of_employees",
        "annual_revenue",
        "currency",
        "address_line",
        "city",
        "state",
        "postcode",
        "country",
        "pages",
    )
    search_fields = ("name", "email", "phone", "website")
    noun = "company"
    plural = "companies"
    salt = "accounts.merge.v1"
