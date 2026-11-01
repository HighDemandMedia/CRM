"""Email-safe brand tokens; inline CSS is required by many mail clients."""

from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_block_tag
def email_section(content, compact=False):
    """Space rendered blocks only when present; email clients cannot rely on :empty."""
    if not content.strip():
        return ""
    return format_html(
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"'
        ' border="0" style="table-layout:fixed;"><tr><td class="email-section"'
        ' style="padding-top:{}px;overflow-wrap:anywhere;word-break:break-word;">'
        "{}</td></tr></table>",
        16 if compact else 24,
        content,
    )


@register.simple_tag
def crm_email_theme():
    return {
        "canvas": "#F1F2F4",
        "surface": "#FFFFFF",
        "secondary": "#E6E8EC",
        "graphite": "#292D30",
        "muted": "#505960",
        "border": "#CDD2D8",
        "red": "#C82322",
        "link": "#A61E1D",
        "button_style": (
            "display:inline-block;box-sizing:border-box;max-width:100%;"
            "padding:12px 24px;background-color:#C82322;"
            "background-image:linear-gradient(135deg,#AC0F0B,#CA4618);"
            "color:#FFFFFF;text-decoration:none;border-radius:24px;"
            "font-size:14px;font-weight:600;line-height:20px;text-align:center;"
            "white-space:normal;overflow-wrap:anywhere;mso-padding-alt:12px 24px;"
        ),
    }
