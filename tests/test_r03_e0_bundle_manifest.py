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

    def test_verify_manifest_detects_tampering(self):
        verifier = SCRIPT.parent / "R03_E0_VERIFY_MANIFEST.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "bundle"
            source.mkdir()
            evidence = source / "sample.json"
            evidence.write_bytes(b'{"interfaces":[]}')
            manifest = root / "manifest.json"
            self.assertEqual(self.run_manifest(source, manifest).returncode, 0)
            def verify():
                return subprocess.run([sys.executable, str(verifier), "--bundle",
                    str(source), "--manifest", str(manifest)], capture_output=True, text=True)
            self.assertEqual(verify().returncode, 0)
            evidence.write_bytes(b'{"interfaces":[1]}')
            self.assertNotEqual(verify().returncode, 0)
            evidence.write_bytes(b'{"interfaces":[]}')
            (source / "additional.json").write_text("{}")
            self.assertNotEqual(verify().returncode, 0)

    def test_verifier_rejects_symlinked_bundle_root(self):
        verifier = SCRIPT.parent / "R03_E0_VERIFY_MANIFEST.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "evidence.txt").write_bytes(b"evidence")
            manifest = root / "manifest.json"
            self.assertEqual(self.run_manifest(source, manifest).returncode, 0)
            alias = root / "alias"
            alias.symlink_to(source, target_is_directory=True)
            result = subprocess.run([sys.executable, str(verifier), "--bundle",
                str(alias), "--manifest", str(manifest)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symbolic link", result.stderr)

    def test_generator_rejects_symlinked_bundle_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "evidence.txt").write_bytes(b"evidence")
            alias = root / "alias"
            alias.symlink_to(source, target_is_directory=True)
            result = self.run_manifest(alias, root / "manifest.json")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symbolic link", result.stderr)

    def test_generator_and_verifier_reject_symlinked_child_directory(self):
        verifier = SCRIPT.parent / "R03_E0_VERIFY_MANIFEST.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            external = root / "external"
            external.mkdir()
            (external / "private.txt").write_bytes(b"not part of bundle")
            (source / "evidence.txt").write_bytes(b"evidence")
            manifest = root / "manifest.json"
            self.assertEqual(self.run_manifest(source, manifest).returncode, 0)
            (source / "linked-directory").symlink_to(external, target_is_directory=True)
            self.assertNotEqual(self.run_manifest(source, root / "second.json").returncode, 0)
            result = subprocess.run([sys.executable, str(verifier), "--bundle",
                str(source), "--manifest", str(manifest)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink", result.stderr)

if __name__ == "__main__":
    unittest.main()
