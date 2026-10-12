import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"persistence"))
import P01_Observed_Subnets as subnets

class SubnetCandidateTests(unittest.TestCase):
    def test_explicit_prefix_groups_without_vlans_or_edges(self):
        rows=[dict(source_asset_id="asset-1",kind="ip",origin="observed",
                   value="192.0.2.10",source_paths=["network.json"])]
        candidates=subnets.subnet_candidates(rows,prefix_length=24)
        self.assertEqual(candidates[0]["candidate_subnet"],"192.0.2.0/24")
        self.assertEqual(candidates[0]["prefix_source"],"operator_supplied")
        self.assertIsNone(candidates[0]["vlan_id"])
        self.assertFalse(candidates[0]["ownership_confirmed"])
        self.assertEqual(candidates[0]["graph_edges"],[])

    def test_invalid_observations_and_prefix_are_denied(self):
        good=[dict(source_asset_id="asset-1",kind="ip",origin="observed",
                   value="192.0.2.10",source_paths=["network.json"])]
        for prefix in (-1,33,True,"24"):
            with self.subTest(prefix=prefix),self.assertRaises(ValueError):
                subnets.subnet_candidates(good,prefix_length=prefix)
        for row in (dict(good[0],value="bad"),dict(good[0],source_paths=[]),
                    dict(good[0],origin="declared"),dict(good[0],kind="mac")):
            with self.subTest(row=row),self.assertRaises(ValueError):
                subnets.subnet_candidates([row],prefix_length=24)
if __name__=="__main__":
    unittest.main()
