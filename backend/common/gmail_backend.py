"""Send Django email through a single authorized Gmail system mailbox."""

import base64
import threading
from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


class GmailDeliveryError(Exception):
    """Safe error text: never include Google responses, tokens or message bodies."""


class GmailEmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(**kwargs)
        self.fail_silently = fail_silently
        names = (
            "GMAIL_SYSTEM_CLIENT_ID",
            "GMAIL_SYSTEM_CLIENT_SECRET",
            "GMAIL_SYSTEM_REFRESH_TOKEN",
            "GMAIL_SYSTEM_SENDER",
        )
        if any(not getattr(settings, name, "").strip() for name in names):
            raise ImproperlyConfigured("The Gmail system sender is not configured.")
        self.sender = settings.GMAIL_SYSTEM_SENDER.strip()
        self.credentials = Credentials(
            token=None,
            refresh_token=settings.GMAIL_SYSTEM_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GMAIL_SYSTEM_CLIENT_ID,
            client_secret=settings.GMAIL_SYSTEM_CLIENT_SECRET,
        )
        self._lock = threading.RLock()

    def send_messages(self, email_messages):
        sent = 0
        with self._lock, requests.Session() as session:
            for email in email_messages or []:
                if not email.recipients():
                    continue
                try:
                    # Reject spoofed From headers instead of silently changing senders.
                    mime = email.message()
                    if (
                        parseaddr(mime.get("From", ""))[1].casefold()
                        != self.sender.casefold()
                    ):
                        raise GmailDeliveryError(
                            "The From address must match the Gmail system sender."
                        )
                    for header in ("Sender", "Resent-From", "Resent-Sender"):
                        if mime.get(header):
                            raise GmailDeliveryError(
                                "Alternate sender headers are not supported."
                            )
                    # Gmail's API determines recipients from the MIME, including Bcc.
                    if email.bcc and not mime.get("Bcc"):
                        mime["Bcc"] = ", ".join(email.bcc)
                    if not self.credentials.valid:
                        self.credentials.refresh(Request(session=session))
                    response = session.post(
                        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                        headers={"Authorization": f"Bearer {self.credentials.token}"},
                        json={
                            "raw": base64.urlsafe_b64encode(mime.as_bytes()).decode(
                                "ascii"
                            )
                        },
                        timeout=30,
                        allow_redirects=False,
                    )
                    if response.status_code != 200:
                        raise GmailDeliveryError(
                            f"Gmail did not accept the message (HTTP {response.status_code})."
                        )
                    sent += 1
                except (GoogleAuthError, requests.RequestException):
                    if not self.fail_silently:
                        raise GmailDeliveryError(
                            "Gmail authorization or connection failed. Check the system sender connection."
                        ) from None
                except GmailDeliveryError:
                    if not self.fail_silently:
                        raise
        return sent
