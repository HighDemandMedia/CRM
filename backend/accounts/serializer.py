from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from accounts.models import Account, AccountEmail, AccountEmailLog
from common.last_activity import ActivityListSerializer, LastActivitySerializerMixin
from common.pipeline_settings import PipelineRulesMixin, stages_for
from common.rbac import VisibleCRMSerializerMixin
from common.serializer import (
    AttachmentsSerializer,
    OrganizationSerializer,
    ProfileSerializer,
    TagsSerializer,
    TeamsSerializer,
    UserSerializer,
)
from contacts.serializer import ContactSerializer

# Note: Removed unused serializer properties that were computed but never used by frontend:
# - get_team_users, get_team_and_assigned_users, get_assigned_users_not_in_teams
# - created_on_arrow (frontend computes its own humanized timestamps)


class AccountSerializer(
    VisibleCRMSerializerMixin, LastActivitySerializerMixin, serializers.ModelSerializer
):
    stage_label = serializers.SerializerMethodField()

    def get_stage_label(self, obj):
        cache = self.__dict__.setdefault("_pipeline_labels", {})
        key = (obj.org_id, obj.__class__.__name__)
        if key not in cache:
            cache[key] = {s["key"]: s["label"] for s in stages_for(obj.org, key[1])}
        return cache[key].get(obj.stage, obj.get_stage_display())

    source_label = serializers.CharField(source="get_source_display", read_only=True)
    """Serializer for reading Account data"""

    created_by = UserSerializer()
    org = OrganizationSerializer()
    tags = TagsSerializer(read_only=True, many=True)
    assigned_to = ProfileSerializer(read_only=True, many=True)
    contacts = ContactSerializer(read_only=True, many=True)
    teams = TeamsSerializer(read_only=True, many=True)
    account_attachment = AttachmentsSerializer(read_only=True, many=True)
    country_display = serializers.SerializerMethodField()
    cases = serializers.SerializerMethodField()
    tasks = serializers.SerializerMethodField()
    opportunities = serializers.SerializerMethodField()
    rollups = serializers.SerializerMethodField()

    @extend_schema_field(str)
    def get_country_display(self, obj):
        return obj.get_country_display() if obj.country else None

    @extend_schema_field(dict)
    def get_rollups(self, obj):
        """What this account is worth, owes and is complaining about.

        Computed by `accounts.views.annotate_rollups`, which is applied on the
        list and detail endpoints. It is deliberately absent, `null`, rather
        than zero-filled anywhere else: a page that was never given the numbers
        should say nothing, not quietly claim every total is zero.
        """
        from accounts.views import ROLLUP_FIELDS

        if not hasattr(obj, ROLLUP_FIELDS[0]):
            return None
        return {field: getattr(obj, field) for field in ROLLUP_FIELDS}

    @extend_schema_field(list)
    def get_cases(self, obj):
        """Return cases linked to this account"""
        return [{"id": str(c.id), "name": c.name} for c in obj.accounts_cases.all()]

    @extend_schema_field(list)
    def get_tasks(self, obj):
        """Return tasks linked to this account"""
        return [{"id": str(t.id), "title": t.title} for t in obj.accounts_tasks.all()]

    @extend_schema_field(list)
    def get_opportunities(self, obj):
        """Return opportunities linked to this account"""
        return [
            {
                "id": str(o.id),
                "name": o.name,
                "stage": o.stage,
                "amount": str(o.amount) if o.amount else "0",
            }
            for o in obj.opportunities.all()
        ]

    class Meta:
        list_serializer_class = ActivityListSerializer
        model = Account
        fields = (
            "id",
            # Core Account Information
            "name",
            "email",
            "phone",
            "website",
            "source",
            "stage",
            "source_label",
            "stage_label",
            "stage_entered_at",
            "pages",
            # Business Information
            "industry",
            "number_of_employees",
            "annual_revenue",
            "currency",
            # Address
            "address_line",
            "appointment_at",
            "language",
            "preferred_communication_channel",
            "city",
            "state",
            "postcode",
            "country",
            "country_display",
            # Assignment
            "assigned_to",
            "teams",
            "contacts",
            # Tags
            "tags",
            # Notes
            "description",
            # Related
            "account_attachment",
            "cases",
            "tasks",
            "opportunities",
            "rollups",
            # System
            "created_by",
            "created_at",
            "updated_at",
            "is_active",
            "org",
            # Per-org custom fields (validated via common.custom_fields)
            "custom_fields",
        )


class AccountListSerializer(AccountSerializer):
    """List/card fields without unrelated detail panels or nested full records."""

    from common.list_serializers import ContactLabelSerializer, OwnerLabelSerializer

    assigned_to = OwnerLabelSerializer(read_only=True, many=True)
    contacts = ContactLabelSerializer(read_only=True, many=True)

    class Meta(AccountSerializer.Meta):
        fields = tuple(
            field
            for field in AccountSerializer.Meta.fields
            if field
            not in (
                "org",
                "teams",
                "account_attachment",
                "cases",
                "tasks",
                "opportunities",
            )
        )


class EmailSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        # `AccountCreateMailView` passes `request_obj=request`, matching the
        # call shape of `AccountCreateSerializer` next door. This class did not
        # pop it and forwarded `**kwargs` straight to `super()`, so DRF's
        # `Serializer.__init__` raised `TypeError` and the endpoint failed on
        # every call it had ever received. The org is derived from the request
        # in the view rather than here, so the value itself is not needed; the
        # kwarg is accepted so the two sibling serializers stay callable the
        # same way.
        kwargs.pop("request_obj", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = AccountEmail
        fields = (
            "message_subject",
            "message_body",
            "timezone",
            "scheduled_date_time",
            "scheduled_later",
            "created_at",
            "from_email",
            "rendered_message_body",
        )

    def validate_message_body(self, message_body):
        count = 0
        for i in message_body:
            if i == "{":
                count += 1
            elif i == "}":
                count -= 1
            if count < 0:
                raise serializers.ValidationError(
                    "Brackets do not match, Enter valid tags."
                )
        if count != 0:
            raise serializers.ValidationError(
                "Brackets do not match, Enter valid tags."
            )
        return message_body


class EmailLogSerializer(serializers.ModelSerializer):
    email = EmailSerializer()

    class Meta:
        model = AccountEmailLog
        fields = ["email", "contact", "is_sent"]


class AccountWriteSerializer(serializers.ModelSerializer):
    """Serializer for API documentation of Account write operations"""

    class Meta:
        model = Account
        fields = [
            "name",
            "phone",
            "email",
            "website",
            "source",
            "stage",
            "pages",
            "industry",
            "number_of_employees",
            "annual_revenue",
            "address_line",
            "appointment_at",
            "language",
            "preferred_communication_channel",
            "city",
            "state",
            "postcode",
            "country",
            "description",
        ]


class AccountCreateSerializer(PipelineRulesMixin, serializers.ModelSerializer):
    """Serializer for creating/updating Account data"""

    website = serializers.URLField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=200,
        error_messages={
            "invalid": "Enter a valid company domain or website URL.",
        },
    )

    def __init__(self, *args, **kwargs):
        request_obj = kwargs.pop("request_obj", None)
        kwargs.pop("account", None)  # Remove unused 'account' parameter passed by views
        super().__init__(*args, **kwargs)
        if request_obj:
            self.org = request_obj.profile.org

    def validate_pages(self, value):
        if not isinstance(value, list) or len(value) > 50:
            raise serializers.ValidationError("Provide up to 50 pages.")
        cleaned = []
        from django.core.exceptions import ValidationError
        from django.core.validators import URLValidator

        validator = URLValidator(schemes=["http", "https"])
        for page in value:
            if not isinstance(page, dict):
                raise serializers.ValidationError("Each page needs a name and link.")
            name, url = (
                str(page.get("name", "")).strip(),
                str(page.get("url", "")).strip(),
            )
            if not name or len(name) > 100 or len(url) > 2000:
                raise serializers.ValidationError(
                    "Each page needs a name (up to 100 characters) and link."
                )
            try:
                validator(url)
            except ValidationError:
                raise serializers.ValidationError(
                    "Page links must be valid HTTP or HTTPS URLs."
                )
            cleaned.append({"name": name, "url": url})
        return cleaned

    def validate(self, attrs):
        from common.validators import payload_id_list
        from contacts.models import Contact

        if "contacts" in self.initial_data:
            ids = payload_id_list(self.initial_data.get("contacts") or [], "contacts")
            if Contact.objects.filter(org=self.org, pk__in=ids).count() != len(
                set(map(str, ids))
            ):
                raise serializers.ValidationError(
                    {"contacts": "Choose contacts from this organization."}
                )
        if "tag_ids" in self.initial_data:
            from common.models import Tags

            ids = payload_id_list(self.initial_data.get("tag_ids") or [], "tag_ids")
            if Tags.objects.filter(org=self.org, pk__in=ids).count() != len(
                set(map(str, ids))
            ):
                raise serializers.ValidationError(
                    {"tag_ids": "Choose tags from this organization."}
                )
        return super().validate(attrs)

    def validate_name(self, name):
        if not name:
            return name
        if self.instance:
            if self.instance.name != name:
                if not Account.objects.filter(name__iexact=name, org=self.org).exists():
                    return name
                raise serializers.ValidationError(
                    "Account already exists with this name"
                )
            return name
        if not Account.objects.filter(name__iexact=name, org=self.org).exists():
            return name
        raise serializers.ValidationError("Account already exists with this name")

    def validate_annual_revenue(self, annual_revenue):
        """Reject negative revenue here rather than letting the database do it.

        `Account` carries a `account_revenue_non_negative` CheckConstraint, so
        the value could never be stored, but with nothing in front of it the
        constraint surfaced as an IntegrityError, i.e. a 500, with no indication
        of which field was at fault. `number_of_employees` is a
        PositiveIntegerField and DRF derives `min_value=0` from it for free,
        which is why the sibling field already answered 400 and this one did not.
        """
        if annual_revenue is not None and annual_revenue < 0:
            raise serializers.ValidationError("Annual revenue cannot be negative.")
        return annual_revenue

    class Meta:
        read_only_fields = ("appointment_at",)
        model = Account
        fields = (
            # Core Account Information
            "name",
            "email",
            "phone",
            "website",
            "source",
            "stage",
            "pages",
            # Business Information
            "industry",
            "number_of_employees",
            "annual_revenue",
            "currency",
            # Address
            "address_line",
            "appointment_at",
            "language",
            "preferred_communication_channel",
            "city",
            "state",
            "postcode",
            "country",
            # Notes
            "description",
            # Status
            "is_active",
        )

    def create(self, validated_data):
        # Default currency from org if not provided and has annual_revenue
        if not validated_data.get("currency") and validated_data.get("annual_revenue"):
            request = self.context.get("request")
            if request and hasattr(request, "profile") and request.profile.org:
                validated_data["currency"] = request.profile.org.default_currency
        return super().create(validated_data)


class AccountDetailEditSwaggerSerializer(serializers.Serializer):
    comment = serializers.CharField()
    account_attachment = serializers.FileField()


class AccountCommentEditSwaggerSerializer(serializers.Serializer):
    comment = serializers.CharField()


class EmailWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountEmail
        fields = (
            "from_email",
            "recipients",
            "message_subject",
            "scheduled_later",
            "timezone",
            "scheduled_date_time",
            "message_body",
        )
