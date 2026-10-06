"""Email-safe brand tokens; inline CSS is required by many mail clients."""

from django import template

register = template.Library()


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
            "display:inline-block;padding:14px 28px;background-color:#C82322;"
            "background-image:linear-gradient(135deg,#AC0F0B,#CA4618);"
            "color:#FFFFFF;text-decoration:none;border-radius:6px;"
            "font-size:16px;font-weight:600;line-height:1.4;text-align:center;"
        ),
    }
