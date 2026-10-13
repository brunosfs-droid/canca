"""Opt-in interface SQL migration remains compatible with existing workspaces."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"persistence"))
import P01_PostgreSQL as pg

class InterfaceMigrationContractTests(unittest.TestCase):
    def test_only_explicit_opt_in_selects_version_eleven(self):
        self.assertEqual(len(pg.INTENT_MIGRATIONS),10)
        self.assertEqual(len(pg.INTERFACE_MIGRATIONS),11)
        self.assertEqual(len(pg.migration_prefix([],intents=True)),10)
        self.assertEqual(len(pg.migration_prefix([],interfaces=True)),11)

    def test_older_workspace_clients_accept_known_version_eleven(self):
        rows=pg.migration_prefix([],interfaces=True)
        self.assertEqual(len(pg.migration_prefix(rows,intents=True)),10)
        self.assertEqual(len(pg.migration_prefix(rows,interfaces=True)),11)
        tampered=list(rows)
        tampered[-1]=(11,"f"*64)
        with self.assertRaisesRegex(pg.PersistenceError,"schema_mismatch"):
            pg.migration_prefix(tampered,intents=True)

    def test_schema_fail_closed_until_grants_and_requires_rls(self):
        sql=pg.INTERFACE_MIGRATIONS[-1].read_text()
        for expected in ("FORCE ROW LEVEL SECURITY","ENABLE ROW LEVEL SECURITY",
                         "workspace_model_allowed(false)","workspace_model_allowed(true)",
                         "PRIMARY KEY (workspace_id,collection_id,observation_id)",
                         "workspace coordinator is active"):
            self.assertIn(expected,sql)
        self.assertNotIn("GRANT ALL",sql)
        self.assertNotIn("FOR UPDATE",sql)
        self.assertNotIn("FOR DELETE",sql)

if __name__=="__main__":
    unittest.main()
