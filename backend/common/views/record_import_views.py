from django.db import IntegrityError
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common import record_import
from common.permissions import HasOrgContext


class RecordImportView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)
    parser_classes = (MultiPartParser,)

    def get(self, request, module):
        return Response(
            record_import.schema(request, module),
            headers={"Cache-Control": "private, no-store"},
        )

    def post(self, request, module):
        record_import.authorize(request, module)
        content = record_import.read_upload(request)
        action = request.data.get("action", "preview")
        if action not in {"preview", "commit"}:
            raise ValidationError("Choose preview or commit.")
        if action == "commit":
            try:
                result = record_import.commit(
                    request,
                    module,
                    content,
                    request.data.get("token"),
                    request.data.get("start", 0),
                )
            except IntegrityError:
                return Response(
                    {
                        "message": "A record conflicts with this import. Preview the file again.",
                    },
                    status=409,
                )
        else:
            result = record_import.preview(request, module, content)
        return Response(result, headers={"Cache-Control": "private, no-store"})
