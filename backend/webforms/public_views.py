"""Anonymous endpoints reached from a customer's website.

No JWT, no session, no portal token. `permission_classes = (AllowAny,)` plus an
empty `authentication_classes` is the pattern `cases/csat_views.py` established
for exactly this.

READ THE ORDER BELOW BEFORE CHANGING IT.

`org_id` comes from the URL and the RLS context is set from it BEFORE anything
queries. This is not a stylistic choice. `web_form` is an org-scoped table, so
under an empty RLS context the lookup returns zero rows on a correctly
configured Postgres. Resolving the form first and reading its org afterwards is
what leaves `/api/public/invoice/`, `/api/public/estimate/` and the CSAT
endpoints answering 404 in production today.

The org id is not a credential and is not treated as one. It selects the
tenant, and the form row is then filtered on it, so a mismatched pair answers
404 like every other miss.
"""

import json
import logging
import uuid
from collections.abc import Mapping
from urllib.parse import urlparse

from django.db import transaction
from django.db.models import F
from django.http import HttpResponse, HttpResponseNotFound
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.request_meta import client_ip, referer
from common.tasks import set_rls_context
from webforms import captcha
from webforms.dynamic_serializer import HONEYPOT_FIELD, build_serializer
from webforms.models import WebForm, WebFormDailyStat, WebFormSubmission
from webforms.service import submit_form
from webforms.tasks import queue_notification
from webforms.throttles import WebFormGlobalThrottle, WebFormIPThrottle

logger = logging.getLogger(__name__)

# Cloudflare's widget posts its token under this name.
CAPTCHA_TOKEN_FIELD = "cf-turnstile-response"


class PublicWebFormMixin:
    permission_classes = (AllowAny,)
    authentication_classes: list = []

    def load_form(self, org_id, form_id):
        """The published form, or None.

        Sets the RLS context first. Every caller answers 404 for None: missing,
        unpublished, and belonging to another org are deliberately
        indistinguishable, so the id space cannot be used to enumerate forms.
        """
        set_rls_context(org_id)
        return WebForm.objects.filter(
            id=form_id, org_id=org_id, is_published=True, org__is_active=True
        ).first()

    def origin_allowed(self, request, form):
        """Whether this request's origin may use this form.

        An empty `allowed_origins` means unrestricted, which is the usable
        default for someone pasting a snippet for the first time. The honeypot,
        the throttles and the optional captcha do not depend on this list, so
        an unconfigured form is not an unprotected one.

        Note that this list is a browser-enforced control, like CORS. A
        non-browser caller sets its own Origin and Referer headers, so this
        never was and never will be a defence against a scripted client. The
        throttles and the captcha are what apply there.
        """
        allowed = form.allowed_origins or []
        if not allowed:
            return True
        origin = request.META.get("HTTP_ORIGIN", "")

        # The iframe embed is a document we serve ourselves, so its fetch is
        # same-origin and carries OUR origin, which is never in a customer's
        # list. Without this, an org that lists an origin for the script embed
        # silently breaks its own iframe embed: the two embeds have different
        # origins for the same form. Found in a browser; the unit tests all
        # passed while it was broken.
        if origin and origin == f"{request.scheme}://{request.get_host()}":
            return True

        if origin:
            return origin in allowed
        # No Origin header, which means a server-side POST rather than a
        # browser. Fall back to Referer prefix matching: weaker, because a
        # non-browser caller sets both headers itself, but better than
        # refusing every legitimate server-side integration.
        ref = request.META.get("HTTP_REFERER", "")
        parsed = urlparse(ref)
        return f"{parsed.scheme}://{parsed.netloc}" in allowed

    def success_payload(self, form):
        """What the visitor is told.

        Identical for an accepted submission and for a honeypot rejection, on
        purpose: a bot that can tell it was caught retries differently.
        """
        if form.success_mode == WebForm.SUCCESS_REDIRECT:
            return {
                "status": "ok",
                "mode": WebForm.SUCCESS_REDIRECT,
                "redirect_url": form.redirect_url,
            }
        return {
            "status": "ok",
            "mode": WebForm.SUCCESS_MESSAGE,
            "message": form.success_message,
        }


class WebFormSubmitView(PublicWebFormMixin, APIView):
    throttle_classes = [WebFormIPThrottle, WebFormGlobalThrottle]

    def post(self, request, org_id, form_id):
        form = self.load_form(org_id, form_id)
        if form is None:
            return Response(
                {"detail": "Form not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if not self.origin_allowed(request, form):
            return Response(
                {"detail": "This form cannot be submitted from this site."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ip = client_ip(request)
        ref = referer(request)

        if not isinstance(request.data, Mapping):
            return Response(
                {"detail": "Submit a JSON object or form fields."}, status=400
            )
        request_id = request.data.get("request_id")
        if request_id:
            try:
                request_id = uuid.UUID(str(request_id))
            except (ValueError, TypeError):
                return Response(
                    {"detail": "Invalid submission identifier."}, status=400
                )
            # A retry of an accepted request does not need a second captcha token.
            if WebFormSubmission.objects.filter(
                form=form, org_id=form.org_id, request_id=request_id
            ).exists():
                return Response(self.success_payload(form))
        serializer = build_serializer(form)(data=request.data)
        if not serializer.is_valid():
            submit_form(
                form,
                {},
                ip=ip,
                referer=ref,
                rejected=WebFormSubmission.REJECTED_INVALID,
                reason="serializer validation failed",
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Honeypot before captcha: a bot that fills the decoy should cost us no
        # outbound HTTP call.
        if serializer.honeypot_tripped():
            submit_form(
                form,
                serializer.lead_values(),
                ip=ip,
                referer=ref,
                rejected=WebFormSubmission.REJECTED_SPAM,
                reason="honeypot",
            )
            return Response(self.success_payload(form), status=status.HTTP_200_OK)

        token = request.data.get(CAPTCHA_TOKEN_FIELD, "")
        if not captcha.verify(form, token, ip):
            submit_form(
                form,
                serializer.lead_values(),
                ip=ip,
                referer=ref,
                rejected=WebFormSubmission.REJECTED_SPAM,
                reason="captcha verification failed",
            )
            return Response(
                {"detail": "Could not verify that you are human. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        submission = submit_form(
            form,
            serializer.lead_values(),
            custom_fields=serializer.custom_values(),
            request_id=request_id,
            ip=ip,
            referer=ref,
        )
        transaction.on_commit(lambda: queue_notification(submission.id, form.org_id))
        return Response(self.success_payload(form), status=status.HTTP_200_OK)


class EmbedViewMixin(PublicWebFormMixin):
    """Shared plumbing for the two embed renderers."""

    def count_view(self, form):
        """Increment today's view counter.

        `get_or_create` then an F() update rather than a read-modify-write, so
        two concurrent renders cannot lose a count.

        Failing to count is never allowed to fail the render. The visitor came
        here for a form, not for our analytics, and losing the lead to protect
        a statistic is the wrong trade.
        """
        try:
            stat, _ = WebFormDailyStat.objects.get_or_create(
                form=form, org_id=form.org_id, date=timezone.localdate()
            )
            WebFormDailyStat.objects.filter(pk=stat.pk).update(views=F("views") + 1)
        except Exception:
            logger.exception("Could not count a view for web form %s", form.id)

    def render_context(self, request, form):
        return {
            "form": form,
            "fields": list(form.fields.select_related("custom_field").all()),
            "submit_url": request.build_absolute_uri(
                f"/api/public/forms/{form.org_id}/{form.id}/submit/"
            ),
            "honeypot": HONEYPOT_FIELD,
        }


class WebFormEmbedView(EmbedViewMixin, APIView):
    """HTML for the iframe embed.

    `@xframe_options_exempt` is not optional. The project runs
    XFrameOptionsMiddleware, which would otherwise set X-Frame-Options on this
    response and make every customer iframe show an empty box.

    That is a deliberate hole in a site-wide clickjacking protection, scoped to
    the one view whose entire purpose is being framed, and narrowed by
    `frame-ancestors` whenever the org has listed origins. It carries no
    session and no tenant data: an attacker who frames it can only submit a
    form that was already public.
    """

    @method_decorator(xframe_options_exempt)
    def get(self, request, org_id, form_id):
        form = self.load_form(org_id, form_id)
        if form is None:
            return HttpResponseNotFound("Form not found.")

        self.count_view(form)
        html = render_to_string(
            "webforms/form.html", self.render_context(request, form)
        )
        response = HttpResponse(html, content_type="text/html; charset=utf-8")
        if form.allowed_origins:
            response["Content-Security-Policy"] = "frame-ancestors " + " ".join(
                form.allowed_origins
            )
        return response


class WebFormEmbedJsView(EmbedViewMixin, APIView):
    """JavaScript that renders the form into the host page.

    The field config is inlined at render time rather than fetched, because a
    `<script>` tag is not subject to CORS. That keeps the cross-origin surface
    down to the single submit route.
    """

    def get(self, request, org_id, form_id):
        form = self.load_form(org_id, form_id)
        if form is None:
            return HttpResponseNotFound(
                "// Form not found.", content_type="application/javascript"
            )

        self.count_view(form)
        context = self.render_context(request, form)
        context["config_json"] = self.config_json(context)
        js = render_to_string("webforms/embed.js", context)
        response = HttpResponse(js, content_type="application/javascript; charset=utf-8")
        response["Cache-Control"] = "no-store"
        return response

    def config_json(self, context):
        """The form's shape as a JSON literal to inline in the script.

        `json.dumps` rather than per-value `escapejs`, for two reasons. Django's
        `escapejs` encodes every hyphen as `\\u002D`, which turns each UUID in
        the output into something unreadable and untestable. And a single
        serialised blob has one escaping rule to reason about instead of one per
        interpolation site.

        Safety: the response is `application/javascript`, so there is no HTML
        parsing context and no `</script>` to break out of, and JSON already
        escapes quotes and backslashes so a value cannot escape its literal.
        U+2028 and U+2029 are escaped explicitly because they are legal in JSON
        but are line terminators to a JavaScript parser.
        """
        form = context["form"]
        payload = {
            "submitUrl": context["submit_url"],
            "honeypot": context["honeypot"],
            "buttonLabel": form.submit_button_label,
            # Only the SITE key. `captcha_secret` must never appear here, and
            # `test_the_script_embed_sends_the_site_key_but_not_the_secret`
            # is what says so.
            "captchaSiteKey": form.captcha_site_key if form.captcha_provider else "",
            "mountId": f"hdm-webform-{form.id}",
            "legacyMountId": f"bottlecrm-webform-{form.id}",
            "fields": [
                {
                    "name": field.input_name,
                    "label": field.label,
                    "placeholder": field.placeholder,
                    "required": field.is_required,
                    "multiline": field.lead_field == "description",
                    "email": field.lead_field == "email",
                }
                for field in context["fields"]
            ],
        }
        # Written as escapes rather than literal characters: these are
        # invisible in an editor and an accidental strip would be silent.
        return (
            json.dumps(payload)
            .replace("\u2028", "\\u2028")
            .replace("\u2029", "\\u2029")
        )


class WebFormConnectJsView(WebFormEmbedJsView):
    """Attach to one explicitly selected HTML form; collect mapped inputs only."""

    def get(self, request, org_id, form_id):
        form = self.load_form(org_id, form_id)
        if form is None:
            return HttpResponseNotFound(
                "// Form not found.", content_type="application/javascript"
            )
        context = self.render_context(request, form)
        config = json.loads(self.config_json(context))
        config["formId"] = str(form.pk)
        for field, row in zip(config["fields"], context["fields"]):
            field["externalName"] = row.external_name or row.input_name
        context["config_json"] = (
            json.dumps(config).replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
        )
        # Never cache the connector: publishing/configuration changes apply on reload.
        response = HttpResponse(
            render_to_string("webforms/connect.js", context),
            content_type="application/javascript; charset=utf-8",
        )
        response["Cache-Control"] = "no-store"
        return response
