import importlib.util
from pathlib import Path
import tempfile
import unittest

path = Path(__file__).resolve().parents[1] / "scripts" / "four_phase_evidence_audit.py"
spec = importlib.util.spec_from_file_location("four_phase_evidence_audit", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PhaseAuditTests(unittest.TestCase):
    def test_source_presence_never_means_phase_is_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for paths in mod.CONTROLS.values():
                for name in paths:
                    file = root / name
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_text("test", encoding="utf-8")
            result = mod.inventory(root)
            self.assertTrue(all(x["source_present"] for x in result["phases"].values()))
            self.assertFalse(result["all_phases_closed"])
            self.assertTrue(all(not x["closed"] for x in result["phases"].values()))

    def test_missing_control_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            result = mod.inventory(Path(directory))
            self.assertFalse(result["phases"]["phase_4_delivery"]["source_present"])


if __name__ == "__main__":
    unittest.main()
