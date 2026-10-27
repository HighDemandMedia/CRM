"""Canonical duplicate keys shared by creation, editing and CSV import."""

from urllib.parse import urlsplit

from common.validators import contact_phone_key


def company_domain(value):
    """Compare hostnames, preserving subdomains other than the www alias."""
    value = str(value or "").strip()
    if not value:
        return ""
    try:
        host = urlsplit(value if "://" in value else "//" + value).hostname or ""
        return (
            host.rstrip(".").lower().removeprefix("www.").encode("idna").decode("ascii")
        )
    except (ValueError, UnicodeError):
        return ""


def record_identity_keys(module, values):
    if module == "contacts":
        keys = {
            "email": str(values.get("email") or "").strip().casefold(),
            "phone": contact_phone_key(values.get("phone")),
        }
    elif module == "companies":
        keys = {"website": company_domain(values.get("website"))}
    elif module == "deals":
        keys = {"name": str(values.get("name") or "").strip().casefold()}
    else:
        keys = {}
    return {field: key for field, key in keys.items() if key}
