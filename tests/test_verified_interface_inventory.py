import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"persistence"))
import P01_Verified_Interface_Inventory as inventory

class InterfaceInventoryTests(unittest.TestCase):
    def test_deduplicates_source_refs_and_bounds_output(self):
        ref={"role":"credentialed_evidence","path":"ssh.json","sha256":"a"*64}
        projection={"observations":[{"source_refs":[ref]},{"source_refs":[ref]}]}
        with patch.object(inventory.registry,"prepare_assets",return_value=projection),patch.object(
                inventory.reader,"read_verified_interfaces",return_value=[{"interface_alias":"eth0"}]) as read:
            result=inventory.inventory(Path("."),Path("."),limit=1)
            self.assertEqual(result["sources"],1)
            self.assertEqual(result["persistence_state"],"not_persisted")
            self.assertEqual(result["topology_edges_created"],0)
            self.assertEqual(len(result["interfaces"]),1)
            read.assert_called_once()

    def test_refuses_unbounded_source_count(self):
        refs=[{"role":"credentialed_evidence","path":str(i),"sha256":"a"*64}
              for i in range(2)]
        with patch.object(inventory.registry,"prepare_assets",
                          return_value={"observations":[{"source_refs":refs}]}),patch.object(
                inventory.reader,"read_verified_interfaces") as read:
            with self.assertRaises(inventory.pg.PersistenceError):
                inventory.inventory(Path("."),Path("."),limit=1)
            read.assert_not_called()

if __name__=="__main__":
    unittest.main()
