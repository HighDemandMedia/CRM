import datetime
import unittest

from check_npm_audit import check


class AuditGateTests(unittest.TestCase):
    def setUp(self):
        self.today = datetime.date(2026, 11, 2)
        self.report = {
            "metadata": {
                "vulnerabilities": {
                    "info": 0,
                    "low": 1,
                    "moderate": 0,
                    "high": 0,
                    "critical": 0,
                }
            },
            "advisories": {
                "1": {
                    "url": "https://github.com/advisories/GHSA-test",
                    "module_name": "package",
                    "findings": [{"version": "1.0.0"}],
                }
            },
        }
        self.exceptions = [
            {
                "id": "GHSA-test",
                "package": "package",
                "version": "1.0.0",
                "expires": "2026-12-02",
                "reason": "Reviewed",
            }
        ]

    def test_reviewed_version_only(self):
        self.assertEqual(check(self.report, self.exceptions, self.today), 1)
        self.report["advisories"]["1"]["findings"][0]["version"] = "1.0.1"
        with self.assertRaises(ValueError):
            check(self.report, self.exceptions, self.today)

    def test_new_advisory_fails(self):
        self.report["advisories"]["1"]["url"] += "-new"
        with self.assertRaises(ValueError):
            check(self.report, self.exceptions, self.today)

    def test_expired_exception_fails(self):
        with self.assertRaises(ValueError):
            check(self.report, self.exceptions, datetime.date(2026, 12, 2))

    def test_failed_or_incomplete_audit_fails(self):
        for report in [
            {},
            {"error": "unavailable"},
            {"advisories": {}},
            {"metadata": {}, "advisories": {"1": {"url": "x"}}},
        ]:
            with self.assertRaises((ValueError, KeyError)):
                check(report, self.exceptions, self.today)

    def test_clean_audit_passes(self):
        self.report["metadata"]["vulnerabilities"]["low"] = 0
        self.report["advisories"] = {}
        self.assertEqual(check(self.report, [], self.today), 0)

    def test_inconsistent_audit_fails(self):
        self.report["advisories"] = {}
        with self.assertRaises(ValueError):
            check(self.report, [], self.today)

    def test_invalid_counts_fail(self):
        for value in (-1, "1", True, None):
            self.report["metadata"]["vulnerabilities"]["low"] = value
            with self.assertRaises(ValueError):
                check(self.report, [], self.today)


if __name__ == "__main__":
    unittest.main()
