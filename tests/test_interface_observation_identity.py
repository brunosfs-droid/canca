import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"persistence"))
import P01_Interface_Observation_Identity as ids

class IdentityTests(unittest.TestCase):
    def test_repeatable_and_workspace_collection_isolated(self):
        item=dict(interface_ordinal=0,source_sha256="a"*64,interface_alias="eth0",address="192.0.2.10")
        one=ids.observation_keys("A","collection-1","a"*64,[item])[0]
        repeat=ids.observation_keys("A","collection-1","a"*64,[item])[0]
        other=ids.observation_keys("B","collection-1","a"*64,[item])[0]
        later=ids.observation_keys("A","collection-2","a"*64,[item])[0]
        self.assertEqual(one["observation_id"],repeat["observation_id"])
        self.assertNotEqual(one["observation_id"],other["observation_id"])
        self.assertNotEqual(one["observation_id"],later["observation_id"])
        self.assertEqual(one["identity_scope"],"observation_only")

    def test_invalid_sha_and_mismatched_source_rejected(self):
        item=dict(interface_ordinal=0,source_sha256="b"*64)
        with self.assertRaises(ValueError):
            ids.observation_keys("A","collection-1","a"*64,[item])
        with self.assertRaises(ValueError):
            ids.observation_keys("A","collection-1","bad",[])
if __name__=="__main__":
    unittest.main()
