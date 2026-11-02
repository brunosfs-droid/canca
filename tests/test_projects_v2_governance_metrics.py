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

    def test_missing_fields_without_reliable_suggestion_are_counted(self):
        missing = mod.gaps_without_suggestion(
            {"Priority": "P1"}, {"Priority": None, "Workstream": "Security", "Target Release": None})
        self.assertEqual(missing, ["Target Release"])

    def test_reports_conflicting_priority_and_workstream_labels(self):
        content = {"labels": {"nodes": [
            {"name": "priority:p0"}, {"name": "priority:p2"},
            {"name": "area:r01"}, {"name": "area:r03"}]}, "milestone": None}
        self.assertEqual(mod.consistency_warnings(content, {}), [
            "multiple_priority_labels", "multiple_workstream_labels"])

    def test_reports_release_milestone_conflict_without_modifying_it(self):
        content = {"labels": {"nodes": []},
                   "milestone": {"title": "Community Beta"}}
        existing = {"Target Release": "Alpha"}
        self.assertEqual(mod.consistency_warnings(content, existing),
                         ["beta_milestone_alpha_release"])
        self.assertEqual(existing["Target Release"], "Alpha")

    def test_no_warning_for_consistent_fields(self):
        content = {"labels": {"nodes": [{"name": "priority:p1"}]},
                   "milestone": {"title": "Product Alpha"}}
        self.assertEqual(mod.consistency_warnings(content, {"Target Release": "Alpha"}), [])

    def test_manual_triage_groups_conflicts_and_missing_options(self):
        changes = [{"number": 11, "field": "Priority", "action": "skipped_missing_option"},
                   {"number": 11, "field": "Workstream", "action": "skipped_missing_option"}]
        findings = [{"number": 11, "rule": "multiple_priority_labels"},
                    {"number": 12, "rule": "alpha_milestone_beta_release"}]
        result = mod.triage_summary(changes, findings, {"Target Release": 3})
        self.assertEqual(result["requires_manual_classification"]["Target Release"], 3)
        self.assertEqual(result["review_items"], [
            {"number": 11, "reason": "classification_conflict",
             "details": ["multiple_priority_labels"]},
            {"number": 11, "reason": "missing_project_option",
             "details": ["Priority", "Workstream"]},
            {"number": 12, "reason": "classification_conflict",
             "details": ["alpha_milestone_beta_release"]},
        ])

    def test_no_classification_is_not_interpreted_as_compliant(self):
        result = mod.audit_metrics([], inspected_items=7)
        self.assertEqual(result["proposed_changes"], 0)
        self.assertEqual(result["inspected_items"], 7)
        self.assertEqual(sum(result["missing_by_field"].values()), 0)


if __name__ == "__main__":
    unittest.main()
