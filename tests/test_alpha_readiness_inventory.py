import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "scripts" / "alpha_readiness_inventory.py"
spec = importlib.util.spec_from_file_location("alpha_readiness_inventory", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AlphaReadinessTests(unittest.TestCase):
    def test_closed_issue_never_implies_operational_acceptance(self):
        items = {number: {"state": "closed", "title": str(number)}
                 for _, number, _, _ in module.GATES}
        result = module.readiness(items)
        self.assertEqual(result["open_gates"], 0)
        self.assertEqual(result["closed_gates"], len(module.GATES))
        self.assertEqual(result["operational_homologation"], "not_verified")
        self.assertEqual(result["release_decision"], "not_assessed")
        self.assertTrue(all(x["evidence_status"] == "not_verified" for x in result["gates"]))

    def test_open_gates_are_counted(self):
        items = {number: {"state": "open", "title": str(number)}
                 for _, number, _, _ in module.GATES}
        result = module.readiness(items)
        self.assertEqual(result["open_gates"], len(module.GATES))
        self.assertEqual(result["closed_gates"], 0)

    def test_unknown_issue_state_is_rejected(self):
        items = {number: {"state": "closed"} for _, number, _, _ in module.GATES}
        items[270]["state"] = "pending"
        with self.assertRaises(ValueError):
            module.readiness(items)


if __name__ == "__main__":
    unittest.main()
