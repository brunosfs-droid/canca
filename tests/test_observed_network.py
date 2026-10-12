"""Network observations remain evidence, not inferred graph ownership."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"persistence"))
import P01_Observed_Network as observed


class ObservedNetworkTests(unittest.TestCase):
    def test_verified_registry_observations_keep_network_source_provenance(self):
        import tempfile
        import test_postgres_assets as assets
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            store,directory=assets.fixture(Path(td)/"source")
            projection=assets.registry.prepare_assets(store,directory)
            rows=observed.project_verified_network_observations(projection)
            self.assertTrue(any(row["kind"]=="ip" and row["value"]=="192.0.2.10"
                                for row in rows))
            self.assertTrue(all(row["source_paths"] and not row["graph_edges"]
                                and not row["ownership_confirmed"] for row in rows))

    def test_forged_network_source_is_rejected(self):
        import copy
        import tempfile
        import test_postgres_assets as assets
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            store,directory=assets.fixture(Path(td)/"source")
            projection=assets.registry.prepare_assets(store,directory)
            forged=copy.deepcopy(projection)
            forged["observations"][0]["signals"][0]["sources"]=["unknown.json"]
            with self.assertRaises(assets.pg.PersistenceError):
                observed.project_verified_network_observations(forged)

    def test_candidates_never_create_topology_edges(self):
        doc={"assets":[{"ip":"192.0.2.10","mac":"AA:BB:CC:DD:EE:FF"},
                       {"ip":"192.0.2.10","mac":"00:11:22:33:44:55"}]}
        rows=observed.project_network_assets(doc)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["observed_mac"],"aa:bb:cc:dd:ee:ff")
        self.assertEqual(rows[0]["observed_ip"],rows[1]["observed_ip"])
        self.assertTrue(all(r["origin"]=="observed" and
                            not r["ownership_confirmed"] and not r["graph_edges"]
                            for r in rows))

    def test_invalid_ip_mac_and_large_input_fail_closed(self):
        for asset in ({"ip":"invalid"},{"ip":"::1"},{"ip":"192.0.2.10","mac":"broken"},
                      {"ip":100},{"ip":"192.0.2.10","mac":True}):
            with self.subTest(asset=asset),self.assertRaises(ValueError):
                observed.project_network_assets({"assets":[asset]})
        with self.assertRaises(ValueError):
            observed.project_network_assets({"assets":[{"ip":"192.0.2.10"}]*1001})


if __name__=="__main__":
    unittest.main()
