"""R02 private staging negative-path tests; no SSH connection."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"server"))
import P01_Workspace_SSH_Adapter as adapter
import P01_Workspace_Service as service
import test_workspace_coordinator as fixtures


class ExportGateTests(unittest.TestCase):
    setUp=fixtures.CoordinatorTests.setUp
    cleanup=fixtures.CoordinatorTests.cleanup
    opened=fixtures.CoordinatorTests.opened

    def test_revoked_write_prevents_private_output(self):
        token=self.opened()
        self.grants["writer"].discard(("A","workspace:write"))
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(service.pg.PersistenceError):
                with self.c.borrow("writer",token,"workspace:write") as operation:
                    adapter.export_verified_ssh_evidence(operation,td,"lab",{"collected":True})
            self.assertEqual(list(Path(td).iterdir()),[])

    def test_existing_evidence_is_never_replaced(self):
        token=self.opened()
        with tempfile.TemporaryDirectory() as td:
            with self.c.borrow("writer",token,"workspace:write") as operation:
                first=adapter.export_verified_ssh_evidence(operation,td,"lab",{"status":"collected"})
                item=Path(td)/first["filename"]
                original=item.read_bytes()
                with self.assertRaises(service.pg.PersistenceError):
                    adapter.export_verified_ssh_evidence(operation,td,"lab",{"status":"collected"})
                self.assertEqual(item.read_bytes(),original)


if __name__=="__main__":
    unittest.main()
