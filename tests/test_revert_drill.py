import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "scripts" / "revert_drill.py"
spec = importlib.util.spec_from_file_location("revert_drill", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class RevertDrillTests(unittest.TestCase):
    def test_revert_restores_clean_nonproduction_baseline(self):
        data = mod.rehearse()
        self.assertTrue(data["restored"])
        self.assertTrue(data["working_tree_clean"])
        self.assertFalse(data["remote_changes"])
        self.assertEqual(data["scope"], "isolated_temp_git_repository")
        self.assertNotEqual(data["test_commit"], data["revert_commit"])


if __name__ == "__main__":
    unittest.main()
