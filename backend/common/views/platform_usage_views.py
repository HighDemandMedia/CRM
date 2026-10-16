"""Read-only platform operations. Organization admins cannot delegate this access."""

from rest_framework import serializers
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.models import Org, User
from common.permissions import HasOrgContext
from common.platform_access import is_platform_owner
from common.platform_usage import CACHE_SECONDS, database_usage, organization_usage


class IsPlatformOwner(BasePermission):
    def has_permission(self, request, view):
        return is_platform_owner(request.user)


class UsageQuery(serializers.Serializer):
    offset = serializers.IntegerField(default=0, min_value=0, max_value=1000000)
    page_size = serializers.ChoiceField(choices=[10, 25, 50, 100], default=25)
    q = serializers.CharField(
        required=False, default="", allow_blank=True, max_length=100
    )


class PlatformUsageView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformOwner, HasOrgContext]

    def get(self, request):
        query = UsageQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        organizations = Org.objects.order_by("name", "id")
        total = organizations.count()
        if params["q"]:
            organizations = organizations.filter(name__icontains=params["q"])
        count = organizations.count() if params["q"] else total
        start, limit = params["offset"], params["page_size"]
        return Response(
            {
                "organizations": total,
                "active_users": User.objects.filter(is_active=True).count(),
                "database": database_usage(),
                "cache_seconds": CACHE_SECONDS,
                "count": count,
                "offset": start,
                "page_size": limit,
                "results": [
                    organization_usage(org)
                    for org in organizations[start : start + limit]
                ],
            },
            headers={"Cache-Control": "private, no-store"},
        )
