"""Rate limits for the public web form submit endpoint.

Two layers, because neither is sufficient alone:

- `WebFormIPThrottle` uses the shared, trusted-proxy-aware client IP resolver.
- `WebFormGlobalThrottle` caps submissions per form across all clients. Header
  rotation cannot evade it, so this is the real backstop.

Both need a shared cache to mean anything across workers. `crm/settings.py`
configures one from `CACHE_URL` and says what happens when it is not set.
"""

from rest_framework.throttling import SimpleRateThrottle

from common.request_meta import client_ip


class WebFormIPThrottle(SimpleRateThrottle):
    scope = "webform_submit_ip"

    def get_cache_key(self, request, view):
        # Bucketed per form as well as per IP, so a visitor who submits one
        # org's form is not locked out of a different org's form.
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"{view.kwargs.get('form_id')}:{client_ip(request) or 'unknown'}",
        }


class WebFormGlobalThrottle(SimpleRateThrottle):
    scope = "webform_submit_global"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": str(view.kwargs.get("form_id")),
        }
