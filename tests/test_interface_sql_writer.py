"""R03 verified SQL writer must refuse ambiguous artifact ownership before SQL."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"persistence"))
import P01_Interface_SQL_Writer as writer

class WriterTests(unittest.TestCase):
    def test_prevalidates_source_mapping_before_connection(self):
        token=Mock()
        entry=dict(interface_ordinal=0,interface_alias='eth0',address='192.0.2.10',
                   prefix_length=24,source_path='ssh.json',source_sha256='a'*64)
        projection={'observations':[{
            'source_asset_id':'asset-1',
            'source_refs':[dict(role='credentialed_evidence',path='ssh.json',sha256='a'*64)]
        }]}
        conn=Mock()
        with patch.object(writer.model,'token_args'),patch.object(writer.inventory,'inventory',
              return_value={'interfaces':[entry]}),patch.object(writer.inventory.registry,
              'prepare_assets',return_value=projection),patch.object(writer.model,'scope') as scope,patch.object(
              writer.pg,'schema_check'):
            result=writer.persist_verified_interfaces(conn,'A',token,Path('.'),Path('.'),'batch-1')
            self.assertEqual(result['observation_count'],1)
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

if __name__=='__main__':
    unittest.main()
