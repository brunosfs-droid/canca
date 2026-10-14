"""R03 verified SQL writer must refuse ambiguous artifact ownership before SQL."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock,MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"persistence"))
import P01_Interface_SQL_Writer as writer

class WriterTests(unittest.TestCase):
    def test_duplicate_observation_identity_fails_before_database_write(self):
        token=Mock()
        item=dict(interface_ordinal=0,interface_alias='eth0',address='192.0.2.10',
                  prefix_length=24,source_path='ssh.json',source_sha256='a'*64)
        conn=MagicMock()
        with patch.object(writer.model,'token_args'),patch.object(
                writer.inventory,'inventory',return_value={'interfaces':[item,item]}),patch.object(
                writer.inventory.registry,'prepare_assets',return_value={'observations':[]}):
            with self.assertRaisesRegex(writer.pg.PersistenceError,'model_import_conflict'):
                writer.persist_verified_interfaces(conn,'A',token,Path('.'),
                                                   Path('.'),'batch-1')
        conn.execute.assert_not_called()
        conn.transaction.assert_not_called()

    def test_prevalidates_source_mapping_before_connection(self):
        token=Mock()
        entry=dict(interface_ordinal=0,interface_alias='eth0',address='192.0.2.10',
                   prefix_length=24,source_path='ssh.json',source_sha256='a'*64)
        projection={'observations':[{
            'source_asset_id':'asset-1',
            'source_refs':[dict(role='credentialed_evidence',path='ssh.json',sha256='a'*64)]
        }]}
        conn=MagicMock()
        conn.execute.return_value.fetchone.return_value=('ifobs-'+'a'*32,)
        with patch.object(writer.model,'token_args'),patch.object(writer.inventory,'inventory',
              return_value={'interfaces':[entry]}),patch.object(writer.inventory.registry,
              'prepare_assets',return_value=projection),patch.object(writer.model,'scope') as scope,patch.object(
              writer.pg,'schema_check'):
            result=writer.persist_verified_interfaces(conn,'A',token,Path('.'),Path('.'),'batch-1')
            self.assertEqual(result['observation_count'],1)
            self.assertEqual(result['inserted_count'],1)
            sql,args=conn.execute.call_args.args
            self.assertIn('workspace_interface_observations',sql)
            self.assertEqual(args[3],'asset-1')
            self.assertEqual(args[8],'192.0.2.10')
            scope.assert_called_once()
        conn.reset_mock()
        with patch.object(writer.model,'token_args'),patch.object(writer.inventory,'inventory',
              return_value={'interfaces':[entry]}),patch.object(writer.inventory.registry,
              'prepare_assets',return_value={'observations':[]}):
            with self.assertRaises(writer.pg.PersistenceError):
                writer.persist_verified_interfaces(conn,'A',token,Path('.'),Path('.'),'batch-1')
            conn.execute.assert_not_called()

    def test_replay_accepts_matching_row_without_new_insert(self):
        token=Mock()
        entry=dict(interface_ordinal=0,interface_alias='eth0',address='192.0.2.10',
                   prefix_length=24,source_path='ssh.json',source_sha256='a'*64)
        projection={'observations':[{
            'source_asset_id':'asset-1',
            'source_refs':[dict(role='credentialed_evidence',path='ssh.json',sha256='a'*64)]
        }]}
        conn=MagicMock()
        prior=('asset-1','ssh.json','a'*64,0,'eth0','192.0.2.10',24)
        conn.execute.return_value.fetchone.side_effect=[None,prior]
        with patch.object(writer.model,'token_args'),patch.object(writer.inventory,'inventory',
              return_value={'interfaces':[entry]}),patch.object(writer.inventory.registry,
              'prepare_assets',return_value=projection),patch.object(writer.model,'scope'),patch.object(
              writer.pg,'schema_check'):
            result=writer.persist_verified_interfaces(conn,'A',token,Path('.'),Path('.'),'batch-1')
        self.assertEqual(result['inserted_count'],0)
        self.assertEqual(conn.execute.call_count,2)

    def test_replay_rejects_divergent_existing_row(self):
        token=Mock()
        entry=dict(interface_ordinal=0,interface_alias='eth0',address='192.0.2.10',
                   prefix_length=24,source_path='ssh.json',source_sha256='a'*64)
        projection={'observations':[{
            'source_asset_id':'asset-1',
            'source_refs':[dict(role='credentialed_evidence',path='ssh.json',sha256='a'*64)]
        }]}
        conn=MagicMock()
        conn.execute.return_value.fetchone.side_effect=[
            None,('DIFFERENT','ssh.json','a'*64,0,'eth0','192.0.2.10',24)]
        with patch.object(writer.model,'token_args'),patch.object(writer.inventory,'inventory',
              return_value={'interfaces':[entry]}),patch.object(writer.inventory.registry,
              'prepare_assets',return_value=projection),patch.object(writer.model,'scope'),patch.object(
              writer.pg,'schema_check'):
            with self.assertRaisesRegex(writer.pg.PersistenceError,'model_import_conflict'):
                writer.persist_verified_interfaces(conn,'A',token,Path('.'),Path('.'),'batch-1')

    def test_sql_exception_rolls_back_transaction_context(self):
        token=Mock()
        entry=dict(interface_ordinal=0,interface_alias='eth0',address='192.0.2.10',
                   prefix_length=24,source_path='ssh.json',source_sha256='a'*64)
        projection={'observations':[{
            'source_asset_id':'asset-1',
            'source_refs':[dict(role='credentialed_evidence',path='ssh.json',sha256='a'*64)]
        }]}
        conn=MagicMock()
        conn.execute.side_effect=RuntimeError('synthetic_sql_failure')
        with patch.object(writer.model,'token_args'),patch.object(writer.inventory,'inventory',
              return_value={'interfaces':[entry]}),patch.object(writer.inventory.registry,
              'prepare_assets',return_value=projection),patch.object(writer.model,'scope'),patch.object(
              writer.pg,'schema_check'):
            with self.assertRaisesRegex(RuntimeError,'synthetic_sql_failure'):
                writer.persist_verified_interfaces(conn,'A',token,Path('.'),Path('.'),'batch-1')
        self.assertEqual(conn.execute.call_count,1)

    def test_ambiguous_credentialed_owners_fail_before_sql(self):
        entry=dict(interface_ordinal=0,interface_alias='eth0',address='192.0.2.10',
                   prefix_length=24,source_path='ssh.json',source_sha256='a'*64)
        projection={'observations':[
            {'source_asset_id':asset,
             'source_refs':[dict(role='credentialed_evidence',
                                 path='ssh.json',sha256='a'*64)]}
            for asset in ('asset-1','asset-2')]}
        conn=MagicMock()
        with patch.object(writer.model,'token_args'),patch.object(
                writer.inventory,'inventory',return_value={'interfaces':[entry]}),patch.object(
                writer.inventory.registry,'prepare_assets',return_value=projection):
            with self.assertRaisesRegex(writer.pg.PersistenceError,'model_import_conflict'):
                writer.persist_verified_interfaces(conn,'A',Mock(),Path('.'),
                                                   Path('.'),'batch-ambiguous')
        conn.execute.assert_not_called()
        conn.transaction.assert_not_called()

    def test_noncredentialed_owner_is_not_accepted(self):
        entry=dict(interface_ordinal=0,interface_alias='eth0',address='192.0.2.10',
                   prefix_length=24,source_path='ssh.json',source_sha256='a'*64)
        projection={'observations':[{
            'source_asset_id':'asset-1',
            'source_refs':[dict(role='network_observation',
                                path='ssh.json',sha256='a'*64)]}]}
        conn=MagicMock()
        with patch.object(writer.model,'token_args'),patch.object(
                writer.inventory,'inventory',return_value={'interfaces':[entry]}),patch.object(
                writer.inventory.registry,'prepare_assets',return_value=projection):
            with self.assertRaisesRegex(writer.pg.PersistenceError,'model_import_conflict'):
                writer.persist_verified_interfaces(conn,'A',Mock(),Path('.'),
                                                   Path('.'),'batch-untrusted')
        conn.execute.assert_not_called()
        conn.transaction.assert_not_called()

    def test_invalid_commit_fence_is_rejected_before_evidence_access(self):
        conn=MagicMock()
        with patch.object(writer.model,'token_args'),patch.object(
                writer.inventory,'inventory') as inventory_read,patch.object(
                writer.inventory.registry,'prepare_assets') as projection_read:
            with self.assertRaisesRegex(writer.pg.PersistenceError,'model_input_invalid'):
                writer.persist_verified_interfaces(conn,'A',Mock(),Path('.'),
                                                   Path('.'),'batch-invalid',
                                                   before_commit='not-callable')
        inventory_read.assert_not_called()
        projection_read.assert_not_called()
        conn.execute.assert_not_called()
        conn.transaction.assert_not_called()

if __name__=='__main__':
    unittest.main()
