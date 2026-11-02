import importlib.util
from pathlib import Path
import unittest

module_path = Path(__file__).resolve().parents[1] / "scripts/security_quality_summary.py"
spec = importlib.util.spec_from_file_location("security_quality_summary", module_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class SecurityQualitySummaryTests(unittest.TestCase):
    def test_counts_findings_by_severity_and_rule(self):
        report = mod.summarize(
            {"results": [{"issue_severity": "HIGH"}, {"issue_severity": "LOW"}], "errors": []},
            [{"code": "E702"}, {"code": "E702"}, {"code": "F401"}],
            {"ssh": {"dependencies": [{"vulns": [{"id": "CVE-test"}]}, {"vulns": []}]}})
        self.assertEqual(report["bandit"]["by_severity"], {"HIGH": 1, "LOW": 1})
        self.assertEqual(report["ruff"]["by_rule"]["E702"], 2)
        self.assertEqual(report["dependencies"]["ssh"]["vulnerabilities"], 1)

    def test_missing_reports_are_not_zeros(self):
        result = mod.summarize(None, None, {"ssh": None})
        self.assertEqual(result["bandit"]["status"], "unavailable")
        self.assertNotIn("total", result["bandit"])
        self.assertEqual(result["dependencies"]["ssh"]["status"], "unavailable")

    def test_bandit_errors_are_visible(self):
        result = mod.summarize({"results": [], "errors": ["invalid target"]}, [], {})
        self.assertEqual(result["bandit"]["status"], "scan_error")


if __name__ == "__main__":
    unittest.main()
