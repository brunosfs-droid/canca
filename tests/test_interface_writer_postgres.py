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

    def test_real_coordinator_session_lease_starts_on_schema_v11(self):
        from psycopg import sql
        import P01_Workspace_Coordinator as runtime
        role='canca_interface_coord_ci'
        if not self.conn.execute(
                'SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone():
            self.conn.execute(sql.SQL(
                'CREATE ROLE {} NOLOGIN NOSUPERUSER NOBYPASSRLS').format(
                    sql.Identifier(role)))
        self.conn.execute(sql.SQL(
            'GRANT USAGE ON SCHEMA canca TO {}').format(sql.Identifier(role)))
        self.conn.execute(sql.SQL(
            'GRANT SELECT ON canca.schema_migrations TO {}').format(sql.Identifier(role)))
        self.conn.execute(sql.SQL(
            'GRANT SELECT,UPDATE ON canca.workspace_runtime TO {}').format(
                sql.Identifier(role)))
        runtime.provision(self.conn,role)
        connection=pg.open_connection()
        self.addCleanup(connection.close)
        connection.execute(sql.SQL('SET ROLE {}').format(sql.Identifier(role)))
        lease=runtime.SessionLease(connection)
        generation=lease.start()
        try:
            self.assertGreaterEqual(generation,1)
            self.assertEqual(lease.transition(generation,'open','A'),generation+1)
        finally:
            lease.stop(generation+1)

    def test_actual_writer_denies_missing_workspace_grant_before_insert(self):
        # Exercise the real workspace scope/RLS contract rather than patching it.
        import P01_Workspace_Coordinator as runtime
        item=dict(interface_ordinal=0,interface_alias='eth0',address='192.0.2.10',
                  prefix_length=24,source_path='ssh.json',source_sha256='a'*64)
        projection={'observations':[{'source_asset_id':'asset-a',
            'source_refs':[dict(role='credentialed_evidence',path='ssh.json',
                                sha256='a'*64)]}]}
        token=runtime.Token('A',1,'a'*32)
        with patch.object(writer.inventory,'inventory',
                return_value={'interfaces':[item]}),patch.object(
                writer.inventory.registry,'prepare_assets',return_value=projection):
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_access_denied'):
                writer.persist_verified_interfaces(
                    self.conn,'A',token,Path('.'),Path('.'),'batch-denied')
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM canca.workspace_interface_observations "
            "WHERE collection_id='batch-denied'").fetchone()[0],0)

    def test_actual_writer_inserts_and_replays_on_postgres(self):
        # Real SQL inserts and replay, with scope mocked only to avoid
        # requiring a separately provisioned workspace coordinator lease.
        from contextlib import nullcontext
        item=dict(interface_ordinal=0,interface_alias='eth0',address='192.0.2.10',
                  prefix_length=24,source_path='ssh.json',source_sha256='a'*64)
        projection={'observations':[{
            'source_asset_id':'asset-a',
            'source_refs':[dict(role='credentialed_evidence',
                                path='ssh.json',sha256='a'*64)]}]}
        with patch.object(writer.model,'token_args'),patch.object(
                writer.model,'scope',side_effect=lambda *args,**kwargs: self.conn.transaction()),patch.object(
                writer.inventory,'inventory',return_value={'interfaces':[item]}),patch.object(
                writer.inventory.registry,'prepare_assets',return_value=projection):
            first=writer.persist_verified_interfaces(self.conn,'A',Mock(),Path('.'),
                                                      Path('.'),'batch-1')
            replay=writer.persist_verified_interfaces(self.conn,'A',Mock(),Path('.'),
                                                       Path('.'),'batch-1')
        self.assertEqual(first['inserted_count'],1)
        self.assertEqual(replay['inserted_count'],0)
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM canca.workspace_interface_observations "
            "WHERE workspace_id='A' AND collection_id='batch-1'").fetchone()[0],1)

    def test_commit_fence_revocation_rolls_back_real_insert(self):
        from contextlib import nullcontext
        item=dict(interface_ordinal=0,interface_alias='eth0',address='192.0.2.10',
                  prefix_length=24,source_path='ssh.json',source_sha256='a'*64)
        projection={'observations':[{'source_asset_id':'asset-a',
            'source_refs':[dict(role='credentialed_evidence',path='ssh.json',
                                sha256='a'*64)]}]}
        def revoked():
            raise pg.PersistenceError('workspace_access_denied')
        with patch.object(writer.model,'token_args'),patch.object(
                writer.model,'scope',side_effect=lambda *args,**kwargs: self.conn.transaction()),patch.object(
                writer.inventory,'inventory',return_value={'interfaces':[item]}),patch.object(
                writer.inventory.registry,'prepare_assets',return_value=projection):
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_access_denied'):
                writer.persist_verified_interfaces(
                    self.conn,'A',Mock(),Path('.'),Path('.'),'batch-revoked',
                    before_commit=revoked)
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM canca.workspace_interface_observations "
            "WHERE collection_id='batch-revoked'").fetchone()[0],0)

    def test_conflicting_replay_rejects_existing_sql_row_without_mutation(self):
        from contextlib import nullcontext
        item=dict(interface_ordinal=0,interface_alias='eth0',
                  address='192.0.2.10',prefix_length=24,
                  source_path='ssh.json',source_sha256='a'*64)
        projection={'observations':[{'source_asset_id':'asset-a',
            'source_refs':[dict(role='credentialed_evidence',path='ssh.json',
                                sha256='a'*64)]}]}
        with patch.object(writer.model,'token_args'),patch.object(
                writer.model,'scope',side_effect=lambda *args,**kwargs: self.conn.transaction()),patch.object(
                writer.inventory,'inventory',return_value={'interfaces':[item]}),patch.object(
                writer.inventory.registry,'prepare_assets',return_value=projection):
            first=writer.persist_verified_interfaces(
                self.conn,'A',Mock(),Path('.'),Path('.'),'batch-conflict')
            self.assertEqual(first['inserted_count'],1)
            # Simulate a conflicting existing row. Append-only replay must
            # fail rather than silently treating divergent content as success.
            self.conn.execute(
                "UPDATE canca.workspace_interface_observations "
                "SET source_asset_id='divergent' WHERE workspace_id='A' "
                "AND collection_id='batch-conflict'")
            with self.assertRaisesRegex(pg.PersistenceError,'model_import_conflict'):
                writer.persist_verified_interfaces(
                    self.conn,'A',Mock(),Path('.'),Path('.'),'batch-conflict')
        rows=self.conn.execute(
            "SELECT source_asset_id FROM canca.workspace_interface_observations "
            "WHERE workspace_id='A' AND collection_id='batch-conflict'").fetchall()
        self.assertEqual(rows,[('divergent',)])

    def test_actual_writer_rolls_back_first_insert_if_second_fails(self):
        from contextlib import nullcontext
        items=[dict(interface_ordinal=n,interface_alias='eth0',
                    address='192.0.2.'+str(10+n),prefix_length=24,
                    source_path='ssh.json',source_sha256='a'*64) for n in (0,1)]
        projection={'observations':[{'source_asset_id':'asset-a',
            'source_refs':[dict(role='credentialed_evidence',
                                path='ssh.json',sha256='a'*64)]}]}
        self.conn.execute(
            "CREATE FUNCTION canca.reject_second_interface() RETURNS trigger "
            "LANGUAGE plpgsql AS 'BEGIN IF NEW.interface_ordinal=1 THEN "
            "RAISE EXCEPTION ''synthetic second row failure''; "
            "END IF; RETURN NEW; END'")
        self.conn.execute(
            "CREATE TRIGGER reject_second_interface BEFORE INSERT "
            "ON canca.workspace_interface_observations FOR EACH ROW "
            "EXECUTE FUNCTION canca.reject_second_interface()")
        with patch.object(writer.model,'token_args'),patch.object(
                writer.model,'scope',side_effect=lambda *args,**kwargs: self.conn.transaction()),patch.object(
                writer.inventory,'inventory',return_value={'interfaces':items}),patch.object(
                writer.inventory.registry,'prepare_assets',return_value=projection):
            with self.assertRaisesRegex(Exception,'synthetic second row failure'):
                writer.persist_verified_interfaces(self.conn,'A',Mock(),Path('.'),
                                                   Path('.'),'batch-rollback')
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM canca.workspace_interface_observations "
            "WHERE collection_id='batch-rollback'").fetchone()[0],0)

    def test_retry_after_sql_abort_recovers_without_partial_history(self):
        from contextlib import nullcontext
        items=[dict(interface_ordinal=n,interface_alias='eth0',
                    address='192.0.2.'+str(10+n),prefix_length=24,
                    source_path='ssh.json',source_sha256='a'*64) for n in (0,1)]
        projection={'observations':[{'source_asset_id':'asset-a',
            'source_refs':[dict(role='credentialed_evidence',
                                path='ssh.json',sha256='a'*64)]}]}
        calls=[0]
        def fail_after_first():
            calls[0]+=1
            if calls[0]==1:
                raise pg.PersistenceError('workspace_lease_lost')
        with patch.object(writer.model,'token_args'),patch.object(
                writer.model,'scope',side_effect=lambda *args,**kwargs: self.conn.transaction()),patch.object(
                writer.inventory,'inventory',return_value={'interfaces':items}),patch.object(
                writer.inventory.registry,'prepare_assets',return_value=projection):
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_lease_lost'):
                writer.persist_verified_interfaces(
                    self.conn,'A',Mock(),Path('.'),Path('.'),'batch-recovery',
                    before_commit=fail_after_first)
            self.assertEqual(self.conn.execute(
                "SELECT count(*) FROM canca.workspace_interface_observations "
                "WHERE collection_id='batch-recovery'").fetchone()[0],0)
            restored=writer.persist_verified_interfaces(
                self.conn,'A',Mock(),Path('.'),Path('.'),'batch-recovery',
                before_commit=fail_after_first)
            replay=writer.persist_verified_interfaces(
                self.conn,'A',Mock(),Path('.'),Path('.'),'batch-recovery')
        self.assertEqual(restored['inserted_count'],2)
        self.assertEqual(replay['inserted_count'],0)
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM canca.workspace_interface_observations "
            "WHERE collection_id='batch-recovery'").fetchone()[0],2)

    def test_same_collection_and_evidence_remain_separate_across_workspaces(self):
        # Real SQL primary key must include workspace, not only observation ID.
        item=dict(interface_ordinal=0,interface_alias='eth0',address='192.0.2.10',
                  prefix_length=24,source_path='ssh.json',source_sha256='a'*64)
        projection={'observations':[{'source_asset_id':'asset-a',
            'source_refs':[dict(role='credentialed_evidence',
                                path='ssh.json',sha256='a'*64)]}]}
        with patch.object(writer.model,'token_args'),patch.object(
                writer.model,'scope',side_effect=lambda *args,**kwargs: self.conn.transaction()),patch.object(
                writer.inventory,'inventory',return_value={'interfaces':[item]}),patch.object(
                writer.inventory.registry,'prepare_assets',return_value=projection):
            a=writer.persist_verified_interfaces(self.conn,'A',Mock(),Path('.'),
                                                 Path('.'),'batch-shared')
            b=writer.persist_verified_interfaces(self.conn,'B',Mock(),Path('.'),
                                                 Path('.'),'batch-shared')
            replay_a=writer.persist_verified_interfaces(self.conn,'A',Mock(),Path('.'),
                                                        Path('.'),'batch-shared')
        self.assertEqual((a['inserted_count'],b['inserted_count'],
                          replay_a['inserted_count']),(1,1,0))
        rows=self.conn.execute(
            "SELECT workspace_id,count(*) FROM canca.workspace_interface_observations "
            "WHERE collection_id='batch-shared' GROUP BY workspace_id "
            "ORDER BY workspace_id").fetchall()
        self.assertEqual(rows,[('A',1),('B',1)])

    def test_distinct_collections_preserve_append_only_history_in_one_workspace(self):
        # Re-importing unchanged evidence in a later collection is history,
        # not a replay of the original collection's observation key.
        item=dict(interface_ordinal=0,interface_alias='eth0',address='192.0.2.10',
                  prefix_length=24,source_path='ssh.json',source_sha256='a'*64)
        projection={'observations':[{'source_asset_id':'asset-a',
            'source_refs':[dict(role='credentialed_evidence',
                                path='ssh.json',sha256='a'*64)]}]}
        with patch.object(writer.model,'token_args'),patch.object(
                writer.model,'scope',side_effect=lambda *args,**kwargs: self.conn.transaction()),patch.object(
                writer.inventory,'inventory',return_value={'interfaces':[item]}),patch.object(
                writer.inventory.registry,'prepare_assets',return_value=projection):
            first=writer.persist_verified_interfaces(self.conn,'A',Mock(),Path('.'),
                                                     Path('.'),'batch-1')
            later=writer.persist_verified_interfaces(self.conn,'A',Mock(),Path('.'),
                                                     Path('.'),'batch-2')
            replay=writer.persist_verified_interfaces(self.conn,'A',Mock(),Path('.'),
                                                      Path('.'),'batch-1')
        self.assertEqual((first['inserted_count'],later['inserted_count'],
                          replay['inserted_count']),(1,1,0))
        rows=self.conn.execute(
            "SELECT collection_id,observation_id FROM canca.workspace_interface_observations "
            "WHERE workspace_id='A' AND collection_id IN ('batch-1','batch-2') "
            "ORDER BY collection_id").fetchall()
        self.assertEqual(len(rows),2)
        self.assertEqual([row[0] for row in rows],['batch-1','batch-2'])
        self.assertNotEqual(rows[0][1],rows[1][1])

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
        from psycopg.errors import InsufficientPrivilege
        # The unprivileged probe has no EXECUTE right on the guarded
        # authorization function. Explicit denial is the safe contract.
        with self.assertRaises(InsufficientPrivilege):
            with self.conn.transaction():
                self.conn.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
                self.conn.execute("SELECT set_config('canca.workspace_id','B',true)")
                self.conn.execute("SELECT * FROM canca.workspace_interface_observations").fetchall()
        # A failed PostgreSQL statement aborts its transaction. Verify
        # the write denial in a fresh transaction, not the aborted one.
        values=('A','batch','ifobs-'+'a'*32,'asset','ssh.json','a'*64,
                0,'eth0','192.0.2.10',24)
        with self.assertRaises(InsufficientPrivilege):
            with self.conn.transaction():
                self.conn.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
                self.conn.execute("SELECT set_config('canca.workspace_id','B',true)")
                self.conn.execute(
                    "INSERT INTO canca.workspace_interface_observations "
                    "(workspace_id,collection_id,observation_id,source_asset_id,"
                    "source_path,source_sha256,interface_ordinal,interface_alias,"
                    "ipv4_address,prefix_length) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",values)
