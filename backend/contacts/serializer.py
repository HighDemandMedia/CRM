from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from common.serializer import (
    AttachmentsSerializer,
    OrganizationSerializer,
    ProfileSerializer,
    TagsSerializer,
    TeamsSerializer,
)
from contacts.models import Contact

# Note: Removed unused serializer properties that were computed but never used by frontend:
# - get_team_users, get_team_and_assigned_users, get_assigned_users_not_in_teams
# - created_on_arrow (frontend computes its own humanized timestamps)


class ContactSerializer(serializers.ModelSerializer):
    """Serializer for reading Contact data"""

    last_activity_at = serializers.DateTimeField(read_only=True)
    tag_details = TagsSerializer(source="tags", many=True, read_only=True)
    created_by_email = serializers.CharField(
        source="created_by.email", read_only=True, default=None
    )
    name = serializers.CharField(read_only=True)
    source_label = serializers.CharField(source="get_source_display", read_only=True)
    stage_label = serializers.CharField(source="get_stage_display", read_only=True)
    preferred_communication_channel_label = serializers.CharField(
        source="get_preferred_communication_channel_display", read_only=True
    )

    teams = TeamsSerializer(read_only=True, many=True)
    assigned_to = ProfileSerializer(read_only=True, many=True)
    contact_attachment = AttachmentsSerializer(read_only=True, many=True)
    org = OrganizationSerializer()
    account_detail = serializers.SerializerMethodField()
    linked_accounts = serializers.SerializerMethodField()

    @extend_schema_field(dict)
    def get_account_detail(self, obj):
        """The `account` FK, resolved to something a page can print.

        The bare field is a UUID, so every caller that wanted to show which
        company somebody works for had to either fetch the account separately
        or fall back to `organization` -- which is free text and is frequently
        a *different* company from the linked one.
        """
        if not obj.account_id:
            return None
        return {"id": str(obj.account.id), "name": obj.account.name}

    @extend_schema_field(list)
    def get_linked_accounts(self, obj):
        """Membership of `Account.contacts`, which is the other account link.

        A Contact is joined to an Account twice over: this many-to-many, and
        the `account` FK the model calls "primary". They are independent, and
        in practice it is this one that carries the data -- the accounts page
        builds its people list from it. A caller that reads only the FK shows
        nobody an account; one that reads only the M2M cannot say which of two
        or three is the main one. Both are published so the choice is the
        reader's and is made in the open.
        """
        return [
            {"id": str(account.id), "name": account.name}
            for account in sorted(
                obj.account_contacts.all(),
                key=lambda item: (item.name.lower(), str(item.pk)),
            )
        ]

    class Meta:
        model = Contact
        fields = (
            "id",
            "name",
            "source_label",
            "stage_label",
            "preferred_communication_channel_label",
            # Core Contact Information
            "first_name",
            "last_name",
            "email",
            "phone",
            "source",
            "stage",
            "appointment_at",
            "preferred_communication_channel",
            "language",
            # Professional Information
            "organization",
            "title",
            "department",
            # Communication Preferences
            "do_not_call",
            "linkedin_url",
            # Address
            "address_line",
            "city",
            "state",
            "postcode",
            "country",
            # Assignment
            "assigned_to",
            "teams",
            # Tags
            "tags",
            "tag_details",
            # Notes
            "description",
            # System
            "created_by",
            "created_at",
            "created_by_email",
            "stage_entered_at",
            "last_activity_at",
            "updated_at",
            "is_active",
            "org",
            "account",
            "account_detail",
            "linked_accounts",
            "contact_attachment",
            # Per-org custom fields (validated via common.custom_fields)
            "custom_fields",
        )


class CreateContactSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating Contact data"""

    name = serializers.CharField(required=False, allow_blank=False, max_length=255)

    def validate(self, attrs):
        name = attrs.pop("name", None)
        if name is not None:
            if "first_name" in attrs or "last_name" in attrs:
                raise serializers.ValidationError(
                    {"name": "Send Name or separate names, not both."}
                )
            if self.instance is None or name != self.instance.name:
                attrs["first_name"] = name
                attrs["last_name"] = ""
        errors = {}
        if self.instance is None:
            if not attrs.get("first_name", "").strip():
                errors["name"] = "Name is required."
            for field in ("phone", "source", "stage"):
                if not attrs.get(field):
                    errors[field] = "This field is required."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def __init__(self, *args, **kwargs):
        request_obj = kwargs.pop("request_obj", None)
        super().__init__(*args, **kwargs)
        # Always defined, so that a caller who forgets `request_obj` gets a
        # refusal from the org checks below rather than an AttributeError --
        # or, worse, a check that quietly passes because there was nothing to
        # compare against.
        self.org = request_obj.profile.org if request_obj else None

    def validate_account(self, account):
        """An account from somebody else's org is not a valid link.

        `account` is a plain ModelSerializer field, so DRF resolved it against
        `Account.objects.all()` -- every account in the database, not the ones
        this org can see. Passing a stranger's UUID attached one org's contact
        to another org's account and returned 200. Row-level security stops
        that in a correctly configured deployment, because the lookup runs
        under the tenant policy; it did not stop it here, where the dev role is
        a superuser. The org filter is the contract either way.
        """
        if account is not None and (self.org is None or account.org_id != self.org.id):
            raise serializers.ValidationError("No such account.")
        return account

    def validate_email(self, email):
        if email:
            if self.instance:
                if (
                    Contact.objects.filter(email__iexact=email, org=self.org)
                    .exclude(id=self.instance.id)
                    .exists()
                ):
                    raise serializers.ValidationError(
                        "Contact already exists with this email"
                    )
            else:
                if Contact.objects.filter(email__iexact=email, org=self.org).exists():
                    raise serializers.ValidationError(
                        "Contact already exists with this email"
                    )
        return email

    class Meta:
        model = Contact
        extra_kwargs = {
            "first_name": {"required": False},
            "last_name": {"required": False, "allow_blank": True},
            "phone": {"required": False, "allow_blank": False, "allow_null": False},
            "source": {"required": False, "allow_blank": False, "allow_null": False},
            "stage": {"required": False, "allow_blank": False, "allow_null": False},
        }
        fields = (
            "name",
            # Core Contact Information
            "first_name",
            "last_name",
            "email",
            "phone",
            "source",
            "stage",
            "appointment_at",
            "preferred_communication_channel",
            "language",
            # Professional Information
            "organization",
            "title",
            "department",
            # Communication Preferences
            "do_not_call",
            "linkedin_url",
            # Address
            "address_line",
            "city",
            "state",
            "postcode",
            "country",
            # Notes
            "description",
            # Account
            "account",
            # Status
            "is_active",
        )


class ContactDetailEditSwaggerSerializer(serializers.Serializer):
    comment = serializers.CharField()
    contact_attachment = serializers.FileField()


class ContactCommentEditSwaggerSerializer(serializers.Serializer):
    comment = serializers.CharField()
