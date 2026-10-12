"""Verified reader never projects unauthenticated or tampered bundle entries."""
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"persistence"))
import P01_Verified_Interfaces as verified

class VerifiedInterfaceReaderTests(unittest.TestCase):
    def test_rejects_mismatched_content_hash_before_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"receipt").mkdir()
            (root/"receipt"/"import-receipt.json").write_text(
                json.dumps({"raw_bundle":"raw.p01bundle"}))
            raw=b'{"authentication":{"success":true}}'
            with zipfile.ZipFile(root/"raw.p01bundle","w") as archive:
                archive.writestr("evidence.json",raw)
            projection={"import":{"artifacts":[{
                "role":"credentialed_evidence","path":"evidence.json",
                "sha256":"a"*64,"size_bytes":len(raw)}]}}
            with patch.object(verified.registry,"prepare_assets",return_value=projection),patch.object(
                verified.interfaces,"project_interfaces") as project:
                with self.assertRaises(verified.pg.PersistenceError):
                    verified.read_verified_interfaces(root,root,"evidence.json","a"*64)
                project.assert_not_called()

    def test_rejects_unlisted_source_before_archive_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(verified.registry,"prepare_assets",
                              return_value={"import":{"artifacts":[]}}):
                with self.assertRaises(verified.pg.PersistenceError):
                    verified.read_verified_interfaces(Path(tmp),Path(tmp),
                                                     "unlisted.json","a"*64)

if __name__=="__main__":
    unittest.main()
