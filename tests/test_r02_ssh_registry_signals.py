"""R02 SSH identity/provenance contract through real Asset Registry, no network."""
import base64
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "persistence"))
import P01_Asset_Registry as registry


class SSHRegistrySignalsTests(unittest.TestCase):
    def setUp(self):
        self.fingerprint = "SHA256:" + base64.b64encode(bytes(range(32))).decode().rstrip("=")
        self.path = "evidence/credentialed/ssh.json"
        self.artifact = {"role": "credentialed_evidence", "path": self.path,
                         "sha256": hashlib.sha256(b"synthetic").hexdigest()}
        self.asset = {"asset_id": "asset-test", "sources": [
            {"sha256": self.artifact["sha256"]}], "addresses": ["192.0.2.10"],
            "conflicts": []}
        self.document = {"metadata": {"enricher_name": "P01-SSH-Credentialed-Enrichment"},
                         "target": {"ip": "192.0.2.10", "protocol": "ssh"},
                         "authentication": {"success": True,
                                            "server_host_key": {"fingerprint_sha256": self.fingerprint}},
                         "enrichment": {"collection_status": "collected",
                                        "identity": {"hostname": "host.example.test"}}}

    def project(self):
        return registry.observation(self.asset, 0, [self.artifact],
                                    {self.path: self.document}, set(), set())

    def test_authenticated_ssh_emits_qualified_fingerprint_with_exact_source(self):
        result = self.project()
        fingerprints = [s for s in result["signals"] if s["kind"] == "ssh_host_key_sha256"]
        self.assertEqual(len(fingerprints), 1)
        self.assertEqual(fingerprints[0]["value"], self.fingerprint)
        self.assertTrue(fingerprints[0]["qualified"])
        self.assertEqual(fingerprints[0]["sources"], [self.path])
        self.assertEqual(result["source_refs"][0]["role"], "credentialed_evidence")

    def test_failed_auth_and_auth_only_cannot_assert_identity(self):
        for auth_success, state in ((False, "collected"), (True, "auth_only")):
            with self.subTest(auth_success=auth_success, state=state):
                self.document["authentication"]["success"] = auth_success
                self.document["enrichment"]["collection_status"] = state
                self.assertFalse(any(s["kind"] == "ssh_host_key_sha256"
                                     for s in self.project()["signals"]))

    def test_invalid_fingerprint_is_never_qualified(self):
        self.document["authentication"]["server_host_key"]["fingerprint_sha256"] = "SHA256:invalid"
        self.assertFalse(any(s["kind"] == "ssh_host_key_sha256"
                             for s in self.project()["signals"]))


if __name__ == "__main__":
    unittest.main()
