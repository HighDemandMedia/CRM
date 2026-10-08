from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.creation_forms import configuration, validate_configuration
from common.models import Org
from common.permissions import HasOrgContext
from common.settings_access import require_settings


class CreationFormView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request):
        require_settings(request.profile, "creation_forms")
        return Response(
            configuration(
                request.profile.org, request.query_params.get("target_model", "Contact")
            )
        )

    @transaction.atomic
    def put(self, request):
        require_settings(request.profile, "creation_forms", manage=True)
        if not isinstance(request.data, dict):
            raise ValidationError("Send a creation form configuration object.")
        org = Org.objects.select_for_update().get(pk=request.profile.org_id)
        target = request.data.get("target_model")
        current = configuration(org, target)
        if request.data.get("revision") != current["revision"]:
            return Response(
                {"errors": "The form or its properties changed. Reload before saving."},
                status=409,
            )
        selected = validate_configuration(org, target, request.data.get("selected"))
        org.creation_forms = {**(org.creation_forms or {}), target: selected}
        org.save(update_fields=["creation_forms", "updated_at"])
        return Response(configuration(org, target))


class CreationFormSchemaView(APIView):
    """Field metadata for any signed-in organization member creating a record."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    def get(self, request, target):
        result = configuration(request.profile.org, target)
        return Response(result, headers={"Cache-Control": "private, no-store"})
