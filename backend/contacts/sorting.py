"""Allowlisted ordering applied before contact pagination."""

from django.db.models import Case, CharField, F, OuterRef, Subquery, Value, When
from django.db.models.functions import Coalesce, Concat, Lower, NullIf, Trim

from accounts.models import Account
from common.models import Profile
from contacts.choices import COMMUNICATION_CHANNELS, CONTACT_SOURCES, CONTACT_STAGES


def order_contacts(queryset, key, descending=False, org=None):
    text_fields = {
        "language",
        "phone",
        "email",
        "address_line",
        "city",
        "postcode",
        "state",
        "description",
    }
    catalogs = {
        "source_label": ("source", CONTACT_SOURCES),
        "stage_label": ("stage", CONTACT_STAGES),
        "preferred_communication_channel_label": (
            "preferred_communication_channel",
            COMMUNICATION_CHANNELS,
        ),
    }
    if org and key == "stage_label":
        from common.pipeline_settings import stages_for

        catalogs["stage_label"] = (
            "stage",
            [(s["key"], s["label"]) for s in stages_for(org, "Contact")],
        )
    if key == "name":
        expression = Trim(Concat("first_name", Value(" "), "last_name"))
    elif key in text_fields:
        expression = F(key)
    elif key in catalogs:
        field, choices = catalogs[key]
        expression = Case(
            *[When(**{field: value}, then=Value(label)) for value, label in choices],
            default=Value(""),
            output_field=CharField(),
        )
    elif key == "owner":
        expression = Subquery(
            Profile.objects.filter(contact_assigned_users=OuterRef("pk"))
            .order_by(Lower("user__email"), "pk")
            .values("user__email")[:1]
        )
    elif key == "account":
        expression = Coalesce(
            "account__name",
            Subquery(
                Account.objects.filter(contacts=OuterRef("pk"))
                .order_by(Lower("name"), "pk")
                .values("name")[:1]
            ),
            "organization",
            output_field=CharField(),
        )
    elif key in {
        "created_at",
        "updated_at",
        "last_activity_at",
        "is_active",
        "do_not_call",
    }:
        expression = F(key)
        return queryset.order_by(
            expression.desc(nulls_last=True)
            if descending
            else expression.asc(nulls_last=True),
            "pk",
        )
    else:
        return queryset.order_by("-created_at", "pk")
    expression = Lower(NullIf(expression, Value(""), output_field=CharField()))
    return queryset.annotate(contact_sort_value=expression).order_by(
        F("contact_sort_value").desc(nulls_last=True)
        if descending
        else F("contact_sort_value").asc(nulls_last=True),
        "pk",
    )
