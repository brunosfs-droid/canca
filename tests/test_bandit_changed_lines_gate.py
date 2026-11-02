import importlib.util
from pathlib import Path
import unittest

script = Path(__file__).resolve().parents[1] / "scripts" / "bandit_changed_lines_gate.py"
spec = importlib.util.spec_from_file_location("bandit_changed_lines_gate", script)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class BanditGateTests(unittest.TestCase):
    def test_high_only_on_added_line(self):
        report = {"results": [
            {"issue_severity": "HIGH", "filename": "server/a.py", "line_number": 12},
            {"issue_severity": "HIGH", "filename": "server/a.py", "line_number": 13},
            {"issue_severity": "MEDIUM", "filename": "server/a.py", "line_number": 12},
            {"issue_severity": "HIGH", "filename": "other.py", "line_number": 12},
        ]}
        self.assertEqual(len(gate.new_high_findings(report, {"server/a.py": {12}})), 1)

    def test_diff_hunk_parser(self):
        self.assertIsNotNone(gate.HUNK.match("@@ -4,0 +12,2 @@"))
        self.assertIsNotNone(gate.HUNK.match("@@ -2 +3 @@"))
        self.assertIsNone(gate.HUNK.match("not a hunk"))

    def test_historical_finding_not_blocked(self):
        report = {"results": [{"issue_severity": "HIGH", "filename": "x.py", "line_number": 6}]}
        self.assertEqual(gate.new_high_findings(report, {"x.py": {7, 8}}), [])


if __name__ == "__main__":
    unittest.main()
