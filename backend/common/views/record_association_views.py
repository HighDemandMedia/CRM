from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account
from common.permissions import HasOrgContext, is_org_admin
from common.rbac import configured, require_record
from contacts.access import assert_contact_access
from contacts.models import Contact
from opportunity.models import Opportunity

MODELS = {"company": Account, "deal": Opportunity, "contact": Contact}


class RecordAssociationView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def records(self, kind):
        if kind not in MODELS:
            raise serializers.ValidationError("Invalid record type.")
        rows = MODELS[kind].objects.filter(org=self.request.profile.org, is_active=True)
        if not configured(self.request.profile) and not is_org_admin(
            self.request.profile
        ):
            rows = rows.filter(
                Q(assigned_to=self.request.profile) | Q(created_by=self.request.user)
            ).distinct()
        return rows

    def context(self, kind, pk, target_kind):
        if (kind, target_kind) not in [
            ("company", "contact"),
            ("company", "deal"),
            ("deal", "contact"),
            ("deal", "company"),
        ]:
            raise serializers.ValidationError("Invalid association type.")
        return get_object_or_404(self.records(kind), pk=pk)

    def get(self, request, kind, pk):
        target_kind = request.query_params.get("kind")
        parent = self.context(kind, pk, target_kind)
        rows = self.records(target_kind)
        search = request.query_params.get("search", "").strip()[:255]
        if target_kind == "contact":
            rows = rows.exclude(pk__in=parent.contacts.values("pk"))
            if kind == "company":
                rows = rows.exclude(account=parent)
            if search:
                rows = rows.filter(
                    Q(first_name__icontains=search)
                    | Q(last_name__icontains=search)
                    | Q(email__icontains=search)
                )
            return Response(
                {
                    "results": [
                        {"id": str(c.pk), "name": c.name or c.email}
                        for c in rows.order_by("first_name", "pk")[:30]
                    ]
                }
            )
        if target_kind == "deal":
            rows = rows.exclude(account=parent)
        elif parent.account_id:
            rows = rows.exclude(pk=parent.account_id)
        if search:
            rows = rows.filter(name__icontains=search)
        return Response(
            {"results": list(rows.order_by("name", "pk").values("id", "name")[:30])}
        )

    @transaction.atomic
    def post(self, request, kind, pk):
        target_kind = request.data.get("kind")
        parent = self.context(kind, pk, target_kind)
        require_record(request.profile, parent, "associations")
        operation = request.data.get("operation")
        if operation not in ("add", "remove"):
            raise serializers.ValidationError("Invalid action.")
        target = get_object_or_404(
            self.records(target_kind),
            pk=serializers.UUIDField().run_validation(request.data.get("target")),
        )
        require_record(request.profile, target, "associations")
        if target_kind == "contact":
            assert_contact_access(request.profile, target)
            target = Contact.objects.select_for_update().get(pk=target.pk)
            if operation == "add":
                parent.contacts.add(target)
            else:
                if kind == "company" and target.account_id == parent.pk:
                    target.account = None
                    target.save(update_fields=["account", "updated_at"])
                parent.contacts.remove(target)
        else:
            deal = parent if kind == "deal" else target
            company = target if kind == "deal" else parent
            deal = Opportunity.objects.select_for_update().get(pk=deal.pk)
            if operation == "add":
                if deal.account_id and deal.account_id != company.pk:
                    raise serializers.ValidationError(
                        "This deal already has a company. Remove that association first."
                    )
                deal.account = company
            elif deal.account_id == company.pk:
                deal.account = None
            else:
                return Response({"saved": True})
            deal.save(update_fields=["account", "updated_at"])
        return Response({"saved": True})
