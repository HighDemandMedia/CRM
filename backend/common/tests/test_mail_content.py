import base64
from unittest.mock import Mock

import pytest

from common.google_sync import message_body
from common.mail_content import readable_mail_body


@pytest.mark.parametrize("mime", ["text/plain", "text/html"])
def test_html_and_mislabeled_html_are_readable(mime):
    source = '<html><head><style>body{color:red}</style></head><body><p>Hello Ana,</p><p>Your quote is ready.</p><ul><li>Design</li><li>Ads</li></ul><a href="https://example.test/quote">View quote</a></body></html>'
    api = Mock()
    body = message_body(
        api,
        "message",
        {
            "mimeType": mime,
            "body": {"data": base64.urlsafe_b64encode(source.encode()).decode()},
        },
    )
    assert "Hello Ana,\n\nYour quote is ready." in body
    assert "• Design\n• Ads" in body
    assert "View quote (https://example.test/quote)" in body
    assert "<" not in body and "color:red" not in body
    api.get.assert_not_called()


def test_cached_and_entity_encoded_markup_is_normalized():
    assert (
        readable_mail_body("&lt;p&gt;Hello &amp;amp; welcome&lt;/p&gt;")
        == "Hello & welcome"
    )
    assert readable_mail_body("<p>Hello<br>World</p>") == "Hello\nWorld"


def test_active_content_and_tracking_are_not_exposed():
    body = readable_mail_body(
        '<p>Safe</p><img src="https://tracker.test/pixel" onerror="steal()"><script>steal()</script><iframe>hidden</iframe><a href="javascript:steal()">Link</a>'
    )
    assert body == "Safe\nLink"


def test_plain_text_and_angle_bracket_addresses_are_preserved():
    body = (
        "Hi <ana@example.test>\n\nBudget < 500 & delivery > 3 days.\n> Previous reply"
    )
    assert readable_mail_body(body) == body


def test_empty_plain_alternative_falls_back_to_html():
    def part(mime, body):
        return {
            "mimeType": mime,
            "body": {"data": base64.urlsafe_b64encode(body.encode()).decode()},
        }

    assert (
        message_body(
            Mock(),
            "id",
            {"parts": [part("text/plain", " "), part("text/html", "<p>Message</p>")]},
        )
        == "Message"
    )
