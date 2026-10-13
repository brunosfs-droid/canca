"""PostgreSQL qualification for atomic interface writer and fail-closed RLS."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"persistence"))
import P01_PostgreSQL as pg
import P01_Interface_SQL_Writer as writer

@unittest.skipUnless(os.environ.get("CANCA_TEST_WORKSPACE_POSTGRES")=="1",
                     "workspace PostgreSQL opt-in required")
class InterfaceWriterSQLTests(unittest.TestCase):
    def setUp(self):
        self.conn=pg.open_connection()
        self.addCleanup(self.conn.close)
        self.conn.execute("DROP SCHEMA IF EXISTS canca CASCADE")
        pg.migrate(self.conn,interfaces=True)
        self.conn.execute("INSERT INTO canca.workspaces(workspace_id,name,organization) "
                          "VALUES ('A','Lab A',''),('B','Lab B','')")

    def test_failed_batch_rolls_back_every_record(self):
        rows=[("A","batch-1","ifobs-"+"a"*32,"asset-a","ssh.json","a"*64,0,
               "eth0","192.0.2.10",24),
              ("A","batch-1","ifobs-"+"b"*32,"asset-a","ssh.json","a"*64,0,
               "eth0","not-an-ip",24)]
        statement=("INSERT INTO canca.workspace_interface_observations "
                   "(workspace_id,collection_id,observation_id,source_asset_id,"
                   "source_path,source_sha256,interface_ordinal,interface_alias,"
                   "ipv4_address,prefix_length) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)")
        with self.assertRaises(Exception):
            with self.conn.transaction():
                for row in rows:
                    self.conn.execute(statement,row)
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM canca.workspace_interface_observations").fetchone()[0],0)

    def test_unprivileged_role_cannot_read_or_write_another_workspace(self):
        from psycopg import sql
        role="canca_interface_probe"
        if not self.conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s",(role,)).fetchone():
            self.conn.execute(sql.SQL("CREATE ROLE {} NOLOGIN NOSUPERUSER NOBYPASSRLS").format(
                sql.Identifier(role)))
        self.conn.execute(sql.SQL("GRANT USAGE ON SCHEMA canca TO {}").format(sql.Identifier(role)))
        self.conn.execute(sql.SQL("GRANT SELECT,INSERT ON canca.workspace_interface_observations TO {}").format(
            sql.Identifier(role)))
        with self.conn.transaction():
            self.conn.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
            self.conn.execute("SELECT set_config('canca.workspace_id','B',true)")
            rows=self.conn.execute("SELECT * FROM canca.workspace_interface_observations").fetchall()
            self.assertEqual(rows,[])
            from psycopg.errors import InsufficientPrivilege
            with self.conn.transaction():
                with self.assertRaises(InsufficientPrivilege):
                    self.conn.execute(
                        "INSERT INTO canca.workspace_interface_observations "
                        "(workspace_id,collection_id,observation_id,source_asset_id,"
                        "source_path,source_sha256,interface_ordinal,interface_alias,"
                        "ipv4_address,prefix_length) VALUES "
                        "('A','batch','ifobs-"+"a"*32+"','asset','ssh.json','"+"a"*64+"',0,'eth0','192.0.2.10',24)")
