"""Password recovery is separate from passwordless authentication."""

import logging
from urllib.parse import urlencode

from celery import shared_task
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from common.models import MagicLinkToken, User

logger = logging.getLogger(__name__)


def revoke_user_sessions(user):
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
    MagicLinkToken.objects.filter(
        email__iexact=user.email, used_at__isnull=True
    ).update(is_used=True, used_at=timezone.now())


def queue_reset_notice(user_id, language):
    try:
        send_password_changed_email.delay(str(user_id), language)
    except Exception:
        # Do not roll back a successful password reset if the mail broker is down.
        logger.error(
            "Password changed notification could not be queued", exc_info=False
        )


def deliver(template, subject, email, context, text):
    html = render_to_string(template, context)
    message = EmailMultiAlternatives(
        subject, text, settings.DEFAULT_FROM_EMAIL, [email]
    )
    message.attach_alternative(html, "text/html")
    message.send()


@shared_task
def send_password_reset_email(email, language="en"):
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if not user:
        return
    query = urlencode(
        {
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
            "lang": language,
        }
    )
    spanish = language == "es"
    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/login/reset?{query}"
    minutes = settings.PASSWORD_RESET_TIMEOUT // 60
    text = (
        f"Restablece tu contraseña: {reset_url}\nEl enlace vence en {minutes} minutos y solo puede usarse una vez. Si no solicitaste este cambio, ignora este correo."
        if spanish
        else f"Reset your password: {reset_url}\nThis link expires in {minutes} minutes and can only be used once. If you did not request this, ignore this email."
    )
    deliver(
        "emails/password_reset.html",
        "Restablece tu contraseña de HDM CRM"
        if spanish
        else "Reset your HDM CRM password",
        user.email,
        {
            "spanish": spanish,
            "email_language": language,
            "reset_url": reset_url,
            "minutes": minutes,
        },
        text,
    )


@shared_task
def send_password_changed_email(user_id, language="en"):
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user:
        spanish = language == "es"
        deliver(
            "emails/password_changed.html",
            "Tu contraseña de HDM CRM cambió"
            if spanish
            else "Your HDM CRM password changed",
            user.email,
            {"spanish": spanish, "email_language": language},
            "Tu contraseña de HDM CRM cambió y se cerraron tus sesiones anteriores. Si no realizaste este cambio, contacta a info@highdemandmedia.com."
            if spanish
            else "Your HDM CRM password changed and your previous sessions were signed out. If you did not make this change, contact info@highdemandmedia.com.",
        )
