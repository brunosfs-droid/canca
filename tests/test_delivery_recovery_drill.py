import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "scripts" / "delivery_recovery_drill.py"
spec = importlib.util.spec_from_file_location("delivery_recovery_drill", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DeliveryRecoveryTests(unittest.TestCase):
    def test_restores_bytes_in_isolated_directory(self):
        with patch.object(module, "git_read", return_value=b"config: valid\n") as read:
            result = module.restore_and_verify("a" * 40, files=(".github/test.yml",))
        self.assertEqual(result["local_restore_rehearsal"], "passed")
        self.assertEqual(result["files_verified"], 1)
        self.assertFalse(result["remote_repository_modified"])
        read.assert_called_once_with("a" * 40, ".github/test.yml")

    def test_rejects_non_commit_identifier(self):
        with self.assertRaises(ValueError):
            module.restore_and_verify("HEAD", files=())

    def test_failure_is_not_reported_as_success(self):
        with patch.object(module, "git_read", side_effect=RuntimeError("missing")):
            with self.assertRaises(RuntimeError):
                module.restore_and_verify("a" * 40, files=("missing.yml",))


if __name__ == "__main__":
    unittest.main()
