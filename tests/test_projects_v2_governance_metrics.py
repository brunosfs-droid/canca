"""Offline tests for Projects V2 classification coverage metrics."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "scripts" / "projects_v2_governance.py"
spec = importlib.util.spec_from_file_location("canca_projects_governance", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class GovernanceMetricsTests(unittest.TestCase):
    def test_only_observed_missing_classifications_are_counted(self):
        changes = [
            {"number": 1, "field": "Priority", "suggested": "P1", "action": "dry_run"},
            {"number": 1, "field": "Workstream", "suggested": "Security", "action": "dry_run"},
            {"number": 2, "field": "Target Release", "suggested": "Alpha",
             "action": "skipped_missing_option"},
        ]
        result = mod.audit_metrics(changes, inspected_items=10)
        self.assertEqual(result["inspected_items"], 10)
        self.assertEqual(result["proposed_changes"], 3)
        self.assertEqual(result["missing_by_field"], {
            "Priority": 1, "Workstream": 1, "Target Release": 1,
        })
        self.assertEqual(result["actions"]["dry_run"], 2)
        self.assertEqual(result["actions"]["skipped_missing_option"], 1)

    def test_no_classification_is_not_interpreted_as_compliant(self):
        result = mod.audit_metrics([], inspected_items=7)
        self.assertEqual(result["proposed_changes"], 0)
        self.assertEqual(result["inspected_items"], 7)
        self.assertEqual(sum(result["missing_by_field"].values()), 0)


if __name__ == "__main__":
    unittest.main()
