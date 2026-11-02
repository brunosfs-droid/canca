import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "scripts" / "projects_v2_dashboard.py"
spec = importlib.util.spec_from_file_location("projects_v2_dashboard", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class GovernanceDashboardTests(unittest.TestCase):
    def test_coverage_and_conflicts(self):
        source = {
            "mode": "dry_run",
            "metrics": {"inspected_items": 10, "missing_total_by_field": {
                "Priority": 2, "Workstream": 0, "Target Release": 5}},
            "consistency_findings": [{"number": 1, "rule": "multiple_priority_labels"}],
            "unclassified_items": [{"number": 2, "fields": ["Priority"]}],
            "manual_triage": {"review_items": []},
        }
        result = mod.dashboard(source)
        self.assertEqual(result["classification_coverage"]["Priority"]["percent"], 80.0)
        self.assertEqual(result["classification_coverage"]["Workstream"]["percent"], 100.0)
        self.assertEqual(result["classification_coverage"]["Target Release"]["missing"], 5)
        self.assertEqual(result["consistency_by_rule"]["multiple_priority_labels"], 1)
        self.assertEqual(result["unclassified_items"], 1)

    def test_empty_project_does_not_fake_perfect_coverage(self):
        result = mod.dashboard({"metrics": {"inspected_items": 0,
            "missing_total_by_field": {"Priority": 0, "Workstream": 0, "Target Release": 0}}})
        self.assertIsNone(result["classification_coverage"]["Priority"]["percent"])

    def test_invalid_counts_fail_closed(self):
        with self.assertRaises(ValueError):
            mod.dashboard({"metrics": {"inspected_items": 1,
                "missing_total_by_field": {"Priority": 2, "Workstream": 0, "Target Release": 0}}})


if __name__ == "__main__":
    unittest.main()
