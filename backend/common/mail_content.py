"""Readable email text without executing markup or fetching remote resources."""

import html
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

MARKUP = re.compile(
    r"<\s*(?:!doctype|html|head|body|div|p|br|table|tr|td|th|a|span|font|"
    r"strong|b|em|i|ul|ol|li|blockquote|h[1-6]|pre|img|style|script)\b[^>]*>",
    re.I,
)


class MailTextParser(HTMLParser):
    blocks = {
        "p",
        "div",
        "tr",
        "table",
        "blockquote",
        "ul",
        "ol",
        "pre",
        *[f"h{i}" for i in range(1, 7)],
    }
    hidden_tags = {"head", "style", "script", "iframe", "object", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag in self.hidden_tags:
            self.hidden.append(tag)
        if self.hidden:
            return
        attrs = dict(attrs)
        if tag in self.blocks or tag == "br":
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append(
                "• " if self.parts and self.parts[-1].endswith("\n") else "\n• "
            )
        elif tag in {"td", "th"}:
            self.parts.append("\t")
        elif tag == "a":
            href = attrs.get("href") or ""
            try:
                safe = urlsplit(href).scheme.lower() in {"http", "https", "mailto"}
            except ValueError:
                safe = False
            self.links.append((href if safe else "", len(self.parts)))

    def handle_endtag(self, tag):
        if self.hidden:
            if tag in self.hidden:
                self.hidden = self.hidden[: self.hidden.index(tag)]
            return
        if tag in self.blocks or tag == "li":
            self.parts.append("\n")
        elif tag == "a" and self.links:
            href, start = self.links.pop()
            label = "".join(self.parts[start:]).strip()
            if href and href != label:
                self.parts.append(f" ({href})")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def readable_mail_body(body, *, is_html=False):
    """Normalize mislabeled/escaped HTML too, including already cached messages.

    The result is always text. Clients must continue escaping it when rendering.
    Normal plain text (including addresses in angle brackets) is left intact.
    """
    source = body or ""
    if not MARKUP.search(source):
        decoded = html.unescape(source)
        if MARKUP.search(decoded):
            source = decoded
        elif not is_html:
            return source
    parser = MailTextParser()
    parser.feed(source)
    parser.close()
    text = "".join(parser.parts).replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
