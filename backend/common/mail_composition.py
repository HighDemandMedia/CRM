"""Bounded, sanitized outgoing mail. Uploads are transient, never record files."""

import hashlib
import mimetypes

import nh3
from rest_framework import serializers

from common.mail_content import readable_mail_body
from common.utils import fit_attachment_file_name

MAIL_ATTACHMENT_MAX_BYTES = 10 * 1024 * 1024
MAIL_ATTACHMENT_MAX_COUNT = 10


def sanitize_message(source):
    cleaned = nh3.clean(
        source,
        tags={
            "p",
            "br",
            "strong",
            "b",
            "em",
            "i",
            "u",
            "s",
            "ul",
            "ol",
            "li",
            "a",
            "blockquote",
        },
        attributes={"a": {"href", "title"}},
        clean_content_tags={"script", "style", "iframe", "object", "template"},
        url_schemes={"https", "http", "mailto"},
    )
    return cleaned, readable_mail_body(cleaned, is_html=True)


def validate_uploads(files):
    if len(files) > MAIL_ATTACHMENT_MAX_COUNT:
        raise serializers.ValidationError("Attach up to 10 files.")
    if sum(file.size for file in files) > MAIL_ATTACHMENT_MAX_BYTES:
        raise serializers.ValidationError("Attachments must total 10 MB or less.")
    return files


def prepare_uploads(files):
    """Read only after record/mailbox authorization and hash actual file contents."""
    prepared = []
    remaining = MAIL_ATTACHMENT_MAX_BYTES
    for file in files:
        content = file.read(remaining + 1)
        remaining -= len(content)
        if remaining < 0:
            raise serializers.ValidationError("Attachments must total 10 MB or less.")
        name = fit_attachment_file_name(
            "".join(char for char in file.name if ord(char) >= 32), 200
        )
        prepared.append(
            {
                "name": name,
                "content": content,
                "type": mimetypes.guess_type(name)[0] or "application/octet-stream",
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    return prepared
