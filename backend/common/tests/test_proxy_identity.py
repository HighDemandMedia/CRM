import hashlib
import hmac
import time
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.http import JsonResponse
from django.test import RequestFactory
from rest_framework.test import APIClient

from common.middleware.proxy_identity import ProxyIdentityMiddleware
from common.request_meta import client_ip
from common.views.password_auth_views import PasswordIPThrottle

# Public test vector, not a deployment credential.
KEY = "ab" * 32
PATH = "/api/auth/password/login/"
BODY = b'{"email":"demo@example.test","password":"fictional"}'


def signed_request(ip="198.51.100.10", timestamp=None, path=PATH, body=BODY):
    timestamp = str(timestamp or int(time.time()))
    payload = "\n".join(
        ("crm-client-v1", timestamp, "POST", path, ip, hashlib.sha256(body).hexdigest())
    )
    signature = hmac.new(
        bytes.fromhex(KEY), payload.encode(), hashlib.sha256
    ).hexdigest()
    return RequestFactory().post(
        path,
        body,
        content_type="application/json",
        REMOTE_ADDR="10.0.0.3",
        HTTP_X_CRM_CLIENT_IP=ip,
        HTTP_X_CRM_CLIENT_TIME=timestamp,
        HTTP_X_CRM_CLIENT_SIGNATURE=signature,
        HTTP_X_FORWARDED_FOR="203.0.113.99, 192.0.2.1",
    )


@pytest.fixture(autouse=True)
def proxy_settings(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "proxy-identity-tests",
        }
    }
    settings.PROXY_SIGNING_KEY = KEY
    settings.TRUSTED_PROXY_HOPS = 0
    settings.TRUSTED_PROXY_CIDRS = ()


def process(request):
    return ProxyIdentityMiddleware(lambda req: JsonResponse({"ip": client_ip(req)}))(
        request
    )


def test_signed_identity_survives_body_parsing_and_ignores_spoofed_xff():
    request = signed_request()
    assert process(request).status_code == 200
    assert client_ip(request) == "198.51.100.10"
    assert request.body == BODY


def test_two_visitors_behind_one_web_have_independent_limits():
    cache.clear()
    try:
        for _ in range(30):
            request = signed_request()
            assert process(request).status_code == 200
            assert PasswordIPThrottle().allow_request(request, None)
        request = signed_request()
        process(request)
        assert not PasswordIPThrottle().allow_request(request, None)
        other = signed_request("198.51.100.11")
        process(other)
        assert PasswordIPThrottle().allow_request(other, None)
    finally:
        cache.clear()


@pytest.mark.parametrize(
    "tamper", ["ip", "time", "signature", "body", "path", "method", "query", "missing"]
)
def test_tampered_context_is_rejected_before_view(tamper):
    request = signed_request()
    if tamper == "ip":
        request.META["HTTP_X_CRM_CLIENT_IP"] = "198.51.100.11"
    elif tamper == "time":
        request.META["HTTP_X_CRM_CLIENT_TIME"] = str(int(time.time()) - 5)
    elif tamper == "signature":
        request.META["HTTP_X_CRM_CLIENT_SIGNATURE"] = "0" * 64
    elif tamper == "body":
        request._body = b"{}"
    elif tamper == "path":
        request.path = "/api/auth/password/register/"
    elif tamper == "method":
        request.method = "GET"
    elif tamper == "query":
        request.META["QUERY_STRING"] = "x=1"
    else:
        request.META.pop("HTTP_X_CRM_CLIENT_SIGNATURE")
    assert process(request).status_code == 400
    assert not hasattr(request, "_verified_client_ip")


@pytest.mark.parametrize("offset", [-61, 61])
def test_expired_or_future_context_is_rejected(offset):
    with patch("common.middleware.proxy_identity.time.time", return_value=1800000000):
        assert process(signed_request(timestamp=1800000000 + offset)).status_code == 400


@pytest.mark.parametrize("ip", ["not-an-ip", "198.51.100.10, 1.1.1.1", "fe80::1%eth0"])
def test_even_signed_invalid_addresses_are_rejected(ip):
    assert process(signed_request(ip)).status_code == 400


def test_ipv6_is_normalized():
    request = signed_request("2001:0db8:0:0:0:0:0:1")
    assert process(request).status_code == 200
    assert client_ip(request) == "2001:db8::1"


def test_unsigned_requests_keep_direct_peer_and_invalid_signed_requests_fail_closed(
    settings,
):
    settings.PROXY_SIGNING_KEY = ""
    request = RequestFactory().post(
        PATH, {}, REMOTE_ADDR="192.0.2.10", HTTP_X_FORWARDED_FOR="1.1.1.1"
    )
    assert process(request).status_code == 200
    assert client_ip(request) == "192.0.2.10"
    assert process(signed_request()).status_code == 400


@pytest.mark.parametrize(
    "prefix", ["", "203.0.113.99, ", "junk, ", "203.0.113.1,203.0.113.2,"]
)
def test_managed_ingress_uses_verified_tail_only(settings, prefix):
    settings.TRUSTED_PROXY_HOPS = 2
    request = RequestFactory().post(
        PATH,
        {},
        REMOTE_ADDR="10.0.0.8",
        HTTP_X_FORWARDED_FOR=prefix + "198.51.100.10, 192.0.2.20",
    )
    assert client_ip(request) == "198.51.100.10"


@pytest.mark.parametrize(
    "header", ["", "198.51.100.10", "junk, 192.0.2.20", "198.51.100.10, junk"]
)
def test_short_or_invalid_trusted_tail_falls_back(settings, header):
    settings.TRUSTED_PROXY_HOPS = 2
    request = RequestFactory().post(
        PATH, {}, REMOTE_ADDR="10.0.0.8", HTTP_X_FORWARDED_FOR=header
    )
    assert client_ip(request) == "10.0.0.8"


def test_wrong_key_oversized_body_and_unapproved_path_are_rejected(settings):
    settings.PROXY_SIGNING_KEY = "cd" * 32
    assert process(signed_request()).status_code == 400
    settings.PROXY_SIGNING_KEY = KEY
    assert process(signed_request(body=b"x" * 65537)).status_code == 400
    assert process(signed_request(path="/api/contacts/")).status_code == 400


@pytest.mark.django_db
def test_valid_signature_does_not_bypass_authentication():
    request = signed_request(path="/api/auth/password/change/", body=b"{}")
    headers = {
        key: value
        for key, value in request.META.items()
        if key.startswith("HTTP_X_CRM_")
    }
    response = APIClient().post(
        request.path, b"{}", content_type="application/json", **headers
    )
    assert response.status_code == 401


def test_shared_node_python_vector():
    with patch("common.middleware.proxy_identity.time.time", return_value=1800000000):
        request = signed_request(timestamp=1800000000)
        assert (
            request.META["HTTP_X_CRM_CLIENT_SIGNATURE"]
            == "4f01d76d8f1564a6d68bbe811512d71362cf404e102219670fc2ff006f4912a4"
        )
        assert process(request).status_code == 200


@pytest.mark.django_db
def test_real_login_endpoint_uses_signed_identity_without_changing_auth_result():
    cache.clear()
    try:
        request = signed_request()
        headers = {
            key: value
            for key, value in request.META.items()
            if key.startswith("HTTP_X_CRM_")
        }
        response = APIClient().post(
            PATH, BODY, content_type="application/json", **headers
        )
        assert response.status_code == 401
        assert len(cache.get("throttle_password_ip_198.51.100.10")) == 1
        assert cache.get("throttle_password_ip_127.0.0.1") is None
    finally:
        cache.clear()


@pytest.mark.parametrize(
    "path",
    [
        "/api/auth/password/reset/request/",
        "/api/auth/password/reset/confirm/",
        "/api/auth/password/invitation/",
    ],
)
def test_public_account_endpoints_verify_signed_client_identity(path):
    request = signed_request(path=path)
    assert process(request).status_code == 200
    tampered = signed_request(path=path)
    tampered.META["HTTP_X_CRM_CLIENT_SIGNATURE"] = "0" * 64
    assert process(tampered).status_code == 400


@pytest.mark.django_db
def test_invitation_preview_uses_visitor_limit_without_exposing_invalid_invitation():
    cache.clear()
    try:
        path = "/api/auth/password/invitation/"
        body = b'{"token":"invalid"}'
        request = signed_request(path=path, body=body)
        headers = {
            key: value
            for key, value in request.META.items()
            if key.startswith("HTTP_X_CRM_")
        }
        response = APIClient().post(
            path, body, content_type="application/json", **headers
        )
        assert response.status_code == 400
        assert "email" not in response.data
        assert len(cache.get("throttle_password_ip_198.51.100.10")) == 1
        assert cache.get("throttle_password_ip_127.0.0.1") is None
    finally:
        cache.clear()
