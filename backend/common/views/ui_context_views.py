"""Small, fresh shell configuration in one authenticated round trip."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.permissions import HasOrgContext
from common.pipeline_settings import OBJECTS
from common.property_layout import layout
from common.views.pipeline_settings_views import pipeline_data
from common.views.role_views import permissions_payload


class UIContextView(APIView):
    # This combines several resources for interactive sessions. Restrict it to
    # JWTs so an org:read API key cannot bypass the individual resource scopes.
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasOrgContext]

    def get(self, request):
        profile = request.profile
        org = profile.org
        return Response(
            {
                "ui_language": request.user.ui_language,
                "setup_step": profile.setup_step,
                "terminology": org.terminology,
                "ticket_settings": {
                    "auto_close_children_on_parent_close": org.auto_close_children_on_parent_close,
                },
                "is_super_admin": profile.is_super_admin,
                "permissions": permissions_payload(profile),
                "property_layout": layout(org),
                "pipelines": {
                    target: pipeline_data(org, target, False) for target in OBJECTS
                },
            },
            headers={"Cache-Control": "private, no-store"},
        )
