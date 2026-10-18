"""`client_ip` has to return an IP or nothing, never a string that merely
looks like one.

`WebFormSubmission.submitted_ip` is a GenericIPAddressField, which maps to a
Postgres `inet` column. Django does not run field validators on `save()`, so an
unvalidated header value surfaces as a 500 from the database rather than as a
clean rejection. That is the whole reason this helper validates.
"""

from django.test import RequestFactory

from common.request_meta import client_ip, referer


def _request(**meta):
    return RequestFactory().post("/api/public/forms/x/y/submit/", **meta)


class TestClientIp:
    def test_untrusted_peer_cannot_select_forwarded_address(self, settings):
        settings.TRUSTED_PROXY_CIDRS = ()
        assert (
            client_ip(
                _request(REMOTE_ADDR="192.0.2.10", HTTP_X_FORWARDED_FOR="203.0.113.50")
            )
            == "192.0.2.10"
        )

    def test_trusted_chain_ignores_forged_prefix(self, settings):
        settings.TRUSTED_PROXY_CIDRS = ("10.0.0.0/24", "192.0.2.0/24")
        request = _request(
            REMOTE_ADDR="10.0.0.1",
            HTTP_X_FORWARDED_FOR="203.0.113.99, 198.51.100.5, 192.0.2.20",
        )
        assert client_ip(request) == "198.51.100.5"

    def test_accepts_ipv6(self, settings):
        settings.TRUSTED_PROXY_CIDRS = ("2001:db8:1::/64",)
        assert (
            client_ip(
                _request(
                    REMOTE_ADDR="2001:db8:1::1", HTTP_X_FORWARDED_FOR="2001:db8:2::5"
                )
            )
            == "2001:db8:2::5"
        )

    def test_rejects_interface_scoped_ipv6(self):
        assert client_ip(_request(REMOTE_ADDR="fe80::1%eth0")) is None

    def test_normalizes_mapped_ipv4(self):
        assert client_ip(_request(REMOTE_ADDR="::ffff:192.0.2.10")) == "192.0.2.10"

    def test_malformed_chain_falls_back_to_peer(self, settings):
        settings.TRUSTED_PROXY_CIDRS = ("10.0.0.0/24",)
        for header in (
            "not-an-ip, 203.0.113.50",
            "203.0.113.50,",
            "1.1.1.1'; DROP TABLE lead; --",
            ",".join(["203.0.113.50"] * 33),
        ):
            assert (
                client_ip(_request(REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR=header))
                == "10.0.0.1"
            )

    def test_no_peer_never_trusts_forwarded_header(self):
        assert (
            client_ip(_request(REMOTE_ADDR="", HTTP_X_FORWARDED_FOR="203.0.113.50"))
            is None
        )

    def test_falls_back_to_remote_addr(self):
        assert client_ip(_request(REMOTE_ADDR="10.0.0.1")) == "10.0.0.1"

    def test_returns_none_when_there_is_no_peer(self):
        request = RequestFactory().post("/x/")
        request.META.pop("REMOTE_ADDR", None)
        assert client_ip(request) is None


class TestReferer:
    def test_returns_the_header(self):
        request = _request(HTTP_REFERER="https://example.com/contact")
        assert referer(request) == "https://example.com/contact"

    def test_truncates_to_the_column_width(self):
        request = _request(HTTP_REFERER="https://example.com/" + "a" * 1000)
        assert len(referer(request)) == 512

    def test_missing_header_is_an_empty_string_not_none(self):
        assert referer(_request()) == ""
