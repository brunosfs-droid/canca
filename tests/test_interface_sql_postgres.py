"""Real PostgreSQL opt-in qualification for workspace interface schema v11."""
import os
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"persistence"))
import P01_PostgreSQL as pg

@unittest.skipUnless(os.environ.get("CANCA_TEST_WORKSPACE_POSTGRES")=="1",
                     "workspace PostgreSQL opt-in required")
class InterfaceMigrationSQLTests(unittest.TestCase):
    def setUp(self):
        self.conn=pg.open_connection()
        self.addCleanup(self.conn.close)
        self.conn.execute("DROP SCHEMA IF EXISTS canca CASCADE")

    def test_migrate_replay_and_force_rls(self):
        first=pg.migrate(self.conn,interfaces=True)
        self.assertEqual(first["migration"],11)
        self.assertEqual(pg.migrate(self.conn,interfaces=True)["status"],"already_migrated")
        self.assertEqual(self.conn.execute(
            "SELECT relrowsecurity,relforcerowsecurity FROM pg_class "
            "WHERE oid='canca.workspace_interface_observations'::regclass"
        ).fetchone(),(True,True))
        policies=self.conn.execute(
            "SELECT policyname,cmd FROM pg_policies WHERE schemaname='canca' "
            "AND tablename='workspace_interface_observations' ORDER BY policyname"
        ).fetchall()
        self.assertEqual({tuple(row) for row in policies},
                         {("interface_observation_read","SELECT"),
                          ("interface_observation_write","INSERT")})
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM canca.workspace_interface_observations"
        ).fetchone()[0],0)
        with self.assertRaisesRegex(pg.PersistenceError,"schema_mismatch"):
            pg.schema_check(self.conn,intents=True)

if __name__=="__main__":
    unittest.main()
