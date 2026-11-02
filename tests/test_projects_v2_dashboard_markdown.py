import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "scripts" / "projects_v2_dashboard_markdown.py"
spec = importlib.util.spec_from_file_location("projects_v2_dashboard_markdown", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class DashboardMarkdownTests(unittest.TestCase):
    def test_summary_includes_counts_and_coverage(self):
        data = {"inspected_items": 5, "classification_coverage": {
            "Priority": {"assigned": 4, "missing": 1, "percent": 80},
            "Workstream": {"assigned": 3, "missing": 2, "percent": 60},
            "Target Release": {"assigned": 5, "missing": 0, "percent": 100},
        }, "consistency_findings": 2, "unclassified_items": 1}
        output = mod.render(data)
        self.assertIn("| Priority | 4 | 1 | 80.00% |", output)
        self.assertIn("Consistency findings: **2**", output)
        self.assertIn("read-only", output)

    def test_no_items_is_na_not_full_coverage(self):
        data = {"inspected_items": 0, "classification_coverage": {
            field: {"assigned": 0, "missing": 0, "percent": None}
            for field in ("Priority", "Workstream", "Target Release")
        }, "consistency_findings": 0, "unclassified_items": 0}
        self.assertIn("| Priority | 0 | 0 | N/A |", mod.render(data))


if __name__ == "__main__":
    unittest.main()
