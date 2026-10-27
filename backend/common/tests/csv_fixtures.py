"""Complete otherwise-valid workflow fixtures with the system identity fields.

Tests of missing identifiers opt out. Explicit blank or invalid cells are preserved.
"""

import csv
import io
from itertools import count

_sequence = count(2000000)
_completed = {}


def with_identities(module, content):
    if module not in {"contacts", "companies"}:
        return content
    cache_key = (module, content)
    if cache_key in _completed:
        return _completed[cache_key]
    delimiter = ";" if ";" in content.split("\n", 1)[0] else ","
    try:
        rows = list(csv.reader(io.StringIO(content), delimiter=delimiter, strict=True))
    except csv.Error:
        return content
    if not rows or any(len(row) != len(rows[0]) for row in rows[1:] if row):
        return content
    required = ("email", "phone") if module == "contacts" else ("website",)
    missing = [key for key in required if key not in rows[0]]
    if not missing:
        return content
    headers = rows[0] + missing
    result = io.StringIO()
    writer = csv.writer(result, delimiter=delimiter)
    writer.writerow(headers)
    for row in rows[1:]:
        if not row:
            writer.writerow(row)
            continue
        number = next(_sequence)
        values = {
            "email": f"fixture{number}@example.com",
            "phone": f"+1202{number}",
            "website": f"https://fixture{number}.example.com",
        }
        writer.writerow(row + [values[key] for key in missing])
    _completed[cache_key] = result.getvalue()
    return result.getvalue()
