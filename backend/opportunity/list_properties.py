from django.db.models import Case, CharField, F, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Lower

from common.last_activity import with_last_activity
from common.models import Profile
from common.utils import COUNTRIES, STAGES
from common.validators import date_param, uuid_list_param
from contacts.choices import CONTACT_SOURCES
from contacts.models import Contact


def filter_and_sort(queryset, params):
    contact_ids = uuid_list_param(params, "contacts")
    if contact_ids:
        queryset = queryset.filter(contacts__id__in=contact_ids).distinct()
    if params.get("priority"):
        queryset = queryset.filter(priority=params["priority"])
    for field in ("address_line", "city", "state", "postcode", "country"):
        if params.get(field):
            queryset = queryset.filter(**{f"{field}__icontains": params[field]})
    for bound in ("gte", "lte"):
        value = date_param(params, f"updated_at__{bound}")
        if value:
            queryset = queryset.filter(**{f"updated_at__date__{bound}": value})
    queryset = with_last_activity(queryset)
    sort = params.get("sort")
    expression = None
    if sort in {
        "name",
        "amount",
        "closed_on",
        "address_line",
        "city",
        "state",
        "postcode",
        "created_at",
        "updated_at",
        "last_activity_at",
    }:
        expression = (
            F(sort)
            if sort
            in {"amount", "closed_on", "created_at", "updated_at", "last_activity_at"}
            else Lower(sort)
        )
    elif sort == "account":
        expression = Lower("account__name")
    elif sort == "owner":
        queryset = queryset.annotate(
            sort_owner=Subquery(
                Profile.objects.filter(opportunity_assigned_users=OuterRef("pk"))
                .order_by(Lower("user__email"), "pk")
                .values("user__email")[:1]
            )
        )
        expression = Lower("sort_owner")
    elif sort == "contacts":
        queryset = queryset.annotate(
            sort_contact=Subquery(
                Contact.objects.filter(opportunity_contacts=OuterRef("pk"))
                .order_by(Lower("first_name"), "pk")
                .values("first_name")[:1]
            )
        )
        expression = Lower("sort_contact")
    elif sort in {
        "stage_label",
        "priority_label",
        "lead_source_label",
        "country_label",
    }:
        field, choices = {
            "stage_label": (
                "stage",
                [(value, str(index)) for index, (value, label) in enumerate(STAGES)],
            ),
            "priority_label": (
                "priority",
                [("LOW", "1"), ("MEDIUM", "2"), ("HIGH", "3")],
            ),
            "lead_source_label": ("lead_source", CONTACT_SOURCES),
            "country_label": ("country", COUNTRIES),
        }[sort]
        expression = Case(
            *[
                When(**{field: value}, then=Value(str(label)))
                for value, label in choices
            ],
            output_field=CharField(),
        )
    if expression is not None:
        queryset = queryset.order_by(
            expression.desc(nulls_last=True)
            if params.get("direction") == "desc"
            else expression.asc(nulls_last=True),
            "pk",
        )
    return queryset


def search_properties(queryset, search):
    query = Q()
    for field in (
        "name",
        "description",
        "address_line",
        "city",
        "state",
        "postcode",
        "country",
        "amount",
        "priority",
        "lead_source",
        "account__name",
        "contacts__first_name",
        "contacts__last_name",
        "contacts__email",
        "assigned_to__user__email",
    ):
        query |= Q(**{f"{field}__icontains": search})
    query |= Q(
        stage__in=[
            value for value, label in STAGES if search.casefold() in label.casefold()
        ]
    )
    query |= Q(
        lead_source__in=[
            value
            for value, label in CONTACT_SOURCES
            if search.casefold() in label.casefold()
        ]
    )
    return queryset.filter(query).distinct()
