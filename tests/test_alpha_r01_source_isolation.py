"""R01 negative source-root partition tests, no database/network."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"server"))
import P01_Workspace_Service as service


class WorkspaceSourceIsolationTests(unittest.TestCase):
    def test_wrong_workspace_never_reaches_bundle_reader(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"A"
            root.mkdir()
            sources=service.SourceRoots({"A":root})
            with patch.object(service.model,"prepare_source") as reader:
                with self.assertRaisesRegex(service.pg.PersistenceError,"workspace_access_denied"):
                    sources.prepare("B","LAB-001","bnd-"+"a"*20)
                reader.assert_not_called()

    def test_shared_root_is_never_accepted_for_distinct_workspaces(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"data"
            root.mkdir()
            with self.assertRaises(service.pg.PersistenceError):
                service.SourceRoots({"A":root,"B":root})


if __name__=="__main__":
    unittest.main()
