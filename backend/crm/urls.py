from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views
from django.urls import include, path, register_converter
from django.urls import re_path as url
from django.views.generic import TemplateView
from drf_spectacular.plumbing import DJANGO_PATH_CONVERTER_MAPPING
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from common.converters import UUIDLikeConverter

# Registered on the root URLconf so every app's `<uid:...>` segment resolves.
# See common/converters.py for why this exists and why it is not `<uuid:...>`.
register_converter(UUIDLikeConverter, "uid")

# drf-spectacular maps a converter name to an OpenAPI type; an unknown one
# falls back to a bare string. Without this the published schema would describe
# 165 id path parameters as untyped strings, which is what `<str:pk>` gave us
# and is less than the route now guarantees.
DJANGO_PATH_CONVERTER_MAPPING["uid"] = OpenApiTypes.UUID

app_name = "crm"

urlpatterns = [
    url(
        r"^healthz/$",
        TemplateView.as_view(template_name="healthz.html"),
        name="healthz",
    ),
    path("api/", include("common.app_urls", namespace="common_urls")),
    # Public forms resolve their tenant from the URL and set RLS before reading data.
    path(
        "api/public/forms/",
        include("webforms.public_urls", namespace="public_webforms"),
    ),
    path("api/portal/", include("common.portal_urls", namespace="portal")),
    # Customer self-service portal. Its own credential realm: sign-in under
    # /api/portal/login/ is anonymous, everything else needs a portal token
    # that GetProfileAndOrg refuses anywhere outside this prefix.
    path(
        "logout/", views.LogoutView.as_view(), {"next_page": "/login/"}, name="logout"
    ),
    path("admin/", admin.site.urls),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    # Optional UI:
    path(
        "swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]


if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()

    # MEDIA_ROOT is deliberately NOT served here.
    #
    # It used to be, and the only thing in front of it was RLSContextMiddleware,
    # which asks for *an* org context rather than *the* org. That answered 200
    # with the file to any signed-in user of any tenant, while the record's own
    # endpoint answered the same caller 404. Every uploaded file in the system
    # sat behind it: documents, and lead, deal, ticket and task attachments.
    #
    # Attachments use authenticated download endpoints and record-level permissions.
