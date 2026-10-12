"""R03/R04 immutable evidence and invalid cross-source signal defenses."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"persistence"))
import P01_Workspace_Model as model
import test_postgres_assets as assets


class ProvenanceContractTests(unittest.TestCase):
    def test_model_rejects_undeclared_signal_origin(self):
        with tempfile.TemporaryDirectory() as td:
            store,directory=assets.fixture(Path(td)/"fixture")
            projection=model.prepare_source(store,directory)
            forged=copy.deepcopy(projection)
            forged["observations"][0]["signals"][0]["sources"]=["different-workspace.json"]
            with self.assertRaises(model.pg.PersistenceError):
                model.validate_source(forged)
            self.assertEqual(model.prepare_source(store,directory),projection)

    def test_observation_ids_are_repeatable_on_unmodified_verified_input(self):
        with tempfile.TemporaryDirectory() as td:
            store,directory=assets.fixture(Path(td)/"fixture")
            left=model.prepare_source(store,directory)
            right=model.prepare_source(store,directory)
            self.assertEqual(left["observations"],right["observations"])


if __name__=="__main__":
    unittest.main()
