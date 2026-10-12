"""Credentialed interface projection contracts: no guessed edges."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"persistence"))
import P01_Observed_Interfaces as interfaces

class InterfaceObservationTests(unittest.TestCase):
    def test_explicit_interface_address_keeps_provenance(self):
        evidence={"collection_status":"collected","network":{"interfaces":[
            {"interface_alias":"Ethernet","ipv4":[{"address":"192.0.2.10","prefix_length":24}]}]}}
        rows=interfaces.project_interfaces(evidence,"target.json","a"*64)
        self.assertEqual(rows[0]["interface_alias"],"Ethernet")
        self.assertEqual(rows[0]["prefix_length"],24)
        self.assertEqual(rows[0]["source_path"],"target.json")
        self.assertFalse(rows[0]["ownership_confirmed"])
        self.assertEqual(rows[0]["graph_edges"],[])

    def test_refuse_uncollected_or_unbounded_interface_evidence(self):
        good={"collection_status":"collected","network":{"interfaces":[]}}
        bad=[
            {"collection_status":"failed","network":{"interfaces":[]}},
            {"collection_status":"collected","network":{"interfaces":[{"interface_alias":"x","ipv4":[{"address":"garbage","prefix_length":24}]}]}},
            {"collection_status":"collected","network":{"interfaces":[{"interface_alias":"x","ipv4":[{"address":"192.0.2.10","prefix_length":True}]}]}},
            {"collection_status":"collected","network":{"interfaces":[{}]}},
            {"collection_status":"collected","network":{"interfaces":[{"interface_alias":"x","ipv4":[]}]*257}},
        ]
        for candidate in bad:
            with self.subTest(candidate=candidate),self.assertRaises(ValueError):
                interfaces.project_interfaces(candidate,"target.json","a"*64)
        with self.assertRaises(ValueError):
            interfaces.project_interfaces(good,"target.json","bad")
if __name__=="__main__":
    unittest.main()
