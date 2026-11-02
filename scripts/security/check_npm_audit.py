"""Fail closed on new advisories or expired, version-specific exceptions."""

import datetime
import json
import sys


def check(report, exceptions, today=None):
    today = today or datetime.date.today()
    if report.get("error") or not isinstance(report.get("advisories"), dict):
        raise ValueError("Audit failed or returned an unsupported response")
    metadata = report.get("metadata")
    if not isinstance(metadata, dict) or not isinstance(
        metadata.get("vulnerabilities"), dict
    ):
        raise ValueError("Audit vulnerability metadata missing")
    counts = metadata["vulnerabilities"]
    if any(
        type(counts.get(level)) is not int or counts[level] < 0
        for level in ("info", "low", "moderate", "high", "critical")
    ):
        raise ValueError("Invalid audit vulnerability counts")
    if bool(sum(counts.values())) != bool(report["advisories"]):
        raise ValueError("Audit counts disagree with advisory results")
    allowed = {}
    for item in exceptions:
        if not item.get("reason") or datetime.date.fromisoformat(item["expires"]) <= today:
            raise ValueError(f"Review expired or incomplete exception: {item['id']}")
        allowed[(item["id"], item["package"], item["version"])] = item
    pending = []
    for advisory in report["advisories"].values():
        identifier = advisory["url"].rstrip("/").rsplit("/", 1)[-1]
        findings = advisory.get("findings")
        if not findings:
            raise ValueError(f"Missing affected versions: {identifier}")
        for finding in findings:
            key = (identifier, advisory["module_name"], finding["version"])
            if key not in allowed:
                pending.append(" · ".join(key))
    if pending:
        raise ValueError("Unreviewed vulnerabilities:\n" + "\n".join(sorted(set(pending))))
    return len(report["advisories"])


if __name__ == "__main__":
    try:
        with open(sys.argv[1]) as report_file, open(sys.argv[2]) as exceptions_file:
            count = check(json.load(report_file), json.load(exceptions_file))
        print(f"No unreviewed advisories; {count} explicitly reviewed advisories remain.")
    except (ValueError, KeyError, TypeError, OSError, IndexError) as error:
        sys.exit(str(error))
