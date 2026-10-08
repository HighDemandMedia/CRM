from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import CustomFieldDefinition, Org
from common.permissions import HasOrgContext
from common.property_catalog import FIELDS
from common.property_layout import layout, revision
from common.settings_access import can_access_settings


class PropertyLayoutView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        org = request.profile.org
        return Response({"objects": layout(org), "revision": revision(org)})

    @transaction.atomic
    def put(self, request):
        if not can_access_settings(request.profile, "properties", manage=True):
            return Response(
                {"errors": "Settings management permission required."}, status=403
            )
        org = Org.objects.select_for_update().get(pk=request.profile.org_id)
        target, keys = request.data.get("target_model"), request.data.get("order")
        if target not in FIELDS:
            raise ValidationError("Choose a supported object.")
        if request.data.get("revision") != revision(org):
            return Response(
                {"errors": "Property order changed. Reload before saving."}, status=409
            )
        allowed = (
            set(FIELDS[target])
            | {"last_activity_at"}
            | {
                "custom_fields." + key
                for key in CustomFieldDefinition.objects.filter(
                    org=org, target_model=target
                ).values_list("key", flat=True)
            }
        )
        if (
            not isinstance(keys, list)
            or any(not isinstance(key, str) for key in keys)
            or len(set(keys)) != len(keys)
            or set(keys) != allowed
        ):
            raise ValidationError(
                "Include each current property exactly once. Reload if properties changed."
            )
        org.property_order = {**(org.property_order or {}), target: keys}
        org.save(update_fields=["property_order", "updated_at"])
        return Response({"saved": True, "revision": revision(org)})
