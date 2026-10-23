import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "docs/validation/R03_E0_BUNDLE_MANIFEST.py"

class R03BundleManifestTests(unittest.TestCase):
    def run_manifest(self, source, output):
        return subprocess.run([sys.executable, str(SCRIPT), "--bundle", str(source),
                               "--output", str(output)], capture_output=True, text=True)

    def test_sha256_manifest_and_non_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "sample.json").write_bytes(b'{"interfaces":[]}')
            output = root / "manifest.json"
            result = self.run_manifest(source, output)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(output.read_text())
            self.assertEqual(data["operational_e0"], "pending")
            self.assertEqual(data["source_file_count"], 1)
            self.assertEqual(data["files"][0]["relative_path"], "sample.json")
            self.assertEqual(data["files"][0]["sha256"], hashlib.sha256(b'{"interfaces":[]}').hexdigest())
            self.assertNotEqual(self.run_manifest(source, output).returncode, 0)

    def test_rejects_output_inside_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "file.txt").write_text("data")
            self.assertNotEqual(self.run_manifest(root, root / "manifest.json").returncode, 0)

    def test_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "file.txt").write_text("data")
            (source / "linked.txt").symlink_to(source / "file.txt")
            self.assertNotEqual(self.run_manifest(source, root / "manifest.json").returncode, 0)

if __name__ == "__main__":
    unittest.main()
