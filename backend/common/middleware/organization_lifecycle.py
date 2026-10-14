"""Read-only tenant access while a closure is pending."""

from django.http import JsonResponse
from django.urls import Resolver404, resolve
from django.utils import timezone

from common.models import Org
from common.organization_lifecycle import READ_ONLY_MESSAGE, organization_lock


class OrganizationLifecycleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Lifecycle operations take an exclusive lock inside their service.
        # Authentication and org selection remain available without an org claim.
        if request.path == "/api/org/lifecycle/" or request.path.startswith(
            "/api/auth/"
        ):
            return self.get_response(request)
        request_org = getattr(request, "org", None)
        org_id = getattr(request_org, "pk", None)
        if org_id is None:
            try:
                org_id = resolve(request.path).kwargs.get("org_id")
            except Resolver404:
                pass
        if org_id is None:
            return self.get_response(request)
        mutation = request.method not in (
            "GET",
            "HEAD",
            "OPTIONS",
        ) or request.path.startswith(
            (
                "/api/integrations/google/connect/",
                "/api/integrations/google/callback/",
            )
        )
        if not mutation:
            # Authentication already loaded the organization for this request.
            # Public routes resolve it here; writes still re-read under the lock.
            org = request_org or Org.objects.filter(pk=org_id).first()
            if org and org.deletion_due_at and timezone.now() >= org.deletion_due_at:
                return JsonResponse(
                    {"detail": "This organization's recovery period has ended."},
                    status=403,
                )
            return self.get_response(request)
        with organization_lock(org_id):
            org = Org.objects.filter(pk=org_id).first()
            if not org or not org.is_active:
                return self.get_response(request)
            if org.closing_at:
                if request.path.startswith("/api/public/"):
                    return JsonResponse({"detail": "Not found."}, status=404)
                return JsonResponse(
                    {"detail": READ_ONLY_MESSAGE, "code": "organization_read_only"},
                    status=403,
                )
            return self.get_response(request)
