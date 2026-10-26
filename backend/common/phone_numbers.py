"""Country-aware phone validation; legacy national numbers default to US."""

import re

import phonenumbers

PHONE_ERROR = (
    "Enter a valid phone number for the selected country, without an extension."
)


def phone_e164(value, region="US"):
    """Return E.164 or raise ValueError, never extract digits from arbitrary text."""
    if not isinstance(value, str) or not re.fullmatch(r"\+?[0-9 ().-]+", value.strip()):
        raise ValueError(PHONE_ERROR)
    try:
        number = phonenumbers.parse(value.strip(), region)
    except phonenumbers.NumberParseException:
        raise ValueError(PHONE_ERROR) from None
    if number.extension or not phonenumbers.is_valid_number(number):
        raise ValueError(PHONE_ERROR)
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def valid_phone(value):
    try:
        phone_e164(value)
        return True
    except ValueError:
        return False


def phone_match_key(value):
    """Preserve country codes, including for historical unvalidated records."""
    if not value:
        return ""
    try:
        return phone_e164(value)[1:]
    except ValueError:
        digits = re.sub(r"[^0-9]", "", str(value))
        if str(value).strip().startswith("00"):
            return digits[2:]
        if not str(value).strip().startswith("+") and len(digits) == 10:
            return "1" + digits
        return digits
