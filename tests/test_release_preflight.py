import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "scripts" / "release_preflight.py"
spec = importlib.util.spec_from_file_location("release_preflight", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ReleasePreflightTests(unittest.TestCase):
    def test_successful_checks_never_auto_approve_release(self):
        data = mod.evaluate("v0.7.0-alpha.1", "a" * 40,
                            [{"name": "Python CI", "status": "completed",
                              "conclusion": "success"}])
        self.assertEqual(data["decision"], "review_required")
        self.assertEqual(data["publication"], "not_performed")
        self.assertEqual(data["check_runs_not_successful"], [])

    def test_bad_tag_and_existing_tag_are_rejected(self):
        with self.assertRaises(ValueError):
            mod.evaluate("latest", "a" * 40, [])
        with self.assertRaises(ValueError):
            mod.evaluate("v0.7.0-alpha.1", "a" * 40, [], existing_ref=True)

    def test_failed_or_pending_checks_are_reported(self):
        data = mod.evaluate("v0.7.0-rc.1", "a" * 40, [
            {"name": "CodeQL", "status": "in_progress", "conclusion": None},
            {"name": "Unit Tests", "status": "completed", "conclusion": "failure"}])
        self.assertEqual(data["check_runs_not_successful"], ["CodeQL", "Unit Tests"])


if __name__ == "__main__":
    unittest.main()
