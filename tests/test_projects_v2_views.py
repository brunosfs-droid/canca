import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "scripts" / "projects_v2_views.py"
spec = importlib.util.spec_from_file_location("projects_v2_views", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ProjectsViewsTests(unittest.TestCase):
    def test_project_number_is_passed_as_graphql_int(self):
        from types import SimpleNamespace
        result = SimpleNamespace(returncode=0, stdout='{"data":{"user":null}}', stderr="")
        with patch.object(mod.subprocess, "run", return_value=result) as runner:
            mod.graphql("query", {"owner": "brunosfs-droid", "number": 4})
        argv = runner.call_args.args[0]
        self.assertIn("-F", argv)
        self.assertEqual(argv[argv.index("-F") + 1], "number=4")

    def test_missing_views_proposed_and_existing_views_preserved(self):
        existing = [{"id": "1", "name": "Governance · Overview", "layout": "TABLE_LAYOUT"},
                    {"id": "2", "name": "Existing user view", "layout": "BOARD_LAYOUT"}]
        actions = mod.plan(existing)
        self.assertEqual(actions[0]["action"], "already_exists")
        self.assertEqual([a["action"] for a in actions[1:]], ["create", "create", "create"])
        self.assertEqual(len(existing), 2)

    def test_layout_conflict_requires_review_instead_of_overwrite(self):
        result = mod.plan([{"id": "1", "name": "Governance · Overview",
                            "layout": "BOARD_LAYOUT"}])
        self.assertEqual(result[0]["action"], "review_layout_mismatch")

    def test_already_provisioned_is_idempotent(self):
        existing = [{"name": name, "layout": layout} for name, layout in mod.DESIRED]
        self.assertTrue(all(x["action"] == "already_exists" for x in mod.plan(existing)))


if __name__ == "__main__":
    unittest.main()
