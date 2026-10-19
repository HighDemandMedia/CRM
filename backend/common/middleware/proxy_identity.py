"""Authenticate visitor context from Web before DRF consumes the request body."""

import hashlib
import hmac
import re
import time

from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.http import JsonResponse, RawPostDataException

from common.request_meta import _address

MAX_AGE_SECONDS = 60
MAX_BODY_BYTES = 65536
SIGNED_PATHS = frozenset(
    {
        "/api/auth/password/login/",
        "/api/auth/password/reset/request/",
        "/api/auth/password/reset/confirm/",
        "/api/auth/password/register/",
        "/api/auth/password/invitation/",
        "/api/auth/password/change/",
        "/api/auth/magic-link/request/",
    }
)
HEADER_NAMES = ("IP", "TIME", "SIGNATURE")


class ProxyIdentityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        values = [
            request.META.get(f"HTTP_X_CRM_CLIENT_{name}", "") for name in HEADER_NAMES
        ]
        if any(values):
            if not self.verify(request, *values):
                return JsonResponse({"detail": "Invalid request context."}, status=400)
        return self.get_response(request)

    @staticmethod
    def verify(request, address, timestamp, signature):
        key = settings.PROXY_SIGNING_KEY
        if (
            not key
            or request.method != "POST"
            or request.path not in SIGNED_PATHS
            or request.META.get("QUERY_STRING", "")
            or len(address) > 45
            or not re.fullmatch(r"[0-9]{10}", timestamp)
            or not re.fullmatch(r"[0-9a-f]{64}", signature)
            or abs(time.time() - int(timestamp)) > MAX_AGE_SECONDS
        ):
            return False
        parsed = _address(address)
        if parsed is None or "%" in address or address != address.strip():
            return False
        try:
            # Django also bounds request.body via DATA_UPLOAD_MAX_MEMORY_SIZE.
            body = request.body
        except (RawPostDataException, RequestDataTooBig):
            return False
        if len(body) > MAX_BODY_BYTES:
            return False
        payload = "\n".join(
            (
                "crm-client-v1",
                timestamp,
                request.method,
                request.path,
                address,
                hashlib.sha256(body).hexdigest(),
            )
        )
        expected = hmac.new(
            bytes.fromhex(key), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return False
        # This identifies an IP throttle bucket only. Authentication and tenant
        # authorization still run normally, even when the signature is valid.
        request._verified_client_ip = str(parsed)
        return True
