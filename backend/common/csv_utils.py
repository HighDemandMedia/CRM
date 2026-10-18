"""Spreadsheet-safe values, before the CSV writer handles quoting."""

import re


def csv_safe(value):
    text = str(value if value is not None else "")
    # Quoting CSV syntax alone does not stop spreadsheet formula evaluation.
    if re.match(r"^[\s\ufeff]*[=+\-@]", text) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text
