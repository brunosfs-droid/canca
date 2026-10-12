"""Bounded trusted source handles and coordinator-registered model operations."""
import os
import base64
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import P01_Workspace_Service as service
import test_workspace_coordinator as coordinator
import test_workspace_model as models
import test_postgres_assets as assets
pg,model,runtime=service.pg,service.model,service.runtime

class SourceRootTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.store,self.directory=assets.fixture(self.base/'source')
        self.roots=service.SourceRoots({'A':self.store})
        self.bundle=self.directory.name
    def test_verified_handle_is_repeatable_and_binds_workspace_partition(self):
        self.assertEqual(self.roots.prepare('A','LAB-001',self.bundle),model.prepare_source(self.store,self.directory))
        with self.assertRaisesRegex(pg.PersistenceError,'workspace_access_denied'):
            self.roots.prepare('B','LAB-001',self.bundle)
    def test_invalid_handles_never_reach_source_reader(self):
        with patch.object(model,'prepare_source') as reader:
            for args in (('A','../LAB-001',self.bundle),('A','LAB-001','../'+self.bundle),
                         ('A','LAB-001','bnd-'+'a'*21),('A','LAB-001',None)):
                with self.assertRaises(pg.PersistenceError):self.roots.prepare(*args)
            reader.assert_not_called()
    def test_shared_nested_symlink_and_invalid_roots_rejected(self):
        child=self.store/'child';child.mkdir();alias=self.base/'alias';alias.symlink_to(self.store,target_is_directory=True)
        for roots in ({'A':self.store,'B':self.store},{'A':self.store,'B':child},{'A':alias},
                      {'A':self.base/'absent'},{'A':None},{'../A':self.store}):
            with self.assertRaises(pg.PersistenceError):service.SourceRoots(roots)
    def test_tampered_partition_fails_without_database_access(self):
        receipt=self.directory/'receipt/import-receipt.json';receipt.write_bytes(receipt.read_bytes()+b'tampered')
        with patch.object(pg,'open_connection') as connect:
            with self.assertRaises(pg.PersistenceError):self.roots.prepare('A','LAB-001',self.bundle)
            connect.assert_not_called()

class RegisteredOperationTests(unittest.TestCase):
    setUp=coordinator.CoordinatorTests.setUp
    cleanup=coordinator.CoordinatorTests.cleanup
    opened=coordinator.CoordinatorTests.opened
    def adapter(self):return service.WorkspaceService(self.c,service.SourceRoots({}))
    def test_ssh_package_does_not_call_packager_after_revocation(self):
        token=self.opened()
        adapter=self.adapter()
        self.grants['writer'].discard(('A','workspace:write'))
        with patch('P01_Workspace_SSH_Adapter.package_verified_ssh_bundle') as package:
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_access_denied'):
                adapter.ssh_package_verified('writer',token,'bundle.p01bundle',
                    'LAB-001','R1','NODE-01','network.json',['evidence.json'])
            package.assert_not_called()
        self.assertFalse(self.c._jobs)

    def test_ssh_package_requires_write_and_fences_stale_generation(self):
        token=self.opened()
        adapter=self.adapter()
        with patch('P01_Workspace_SSH_Adapter.package_verified_ssh_bundle',
                   return_value={'bundle_created':True}) as package:
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_access_denied'):
                adapter.ssh_package_verified('reader',token,'output.p01bundle',
                    'LAB-001','R1','NODE-01','network.json',['ssh.json'])
            package.assert_not_called()
            receipt=adapter.ssh_package_verified('writer',token,'output.p01bundle',
                'LAB-001','R1','NODE-01','network.json',['ssh.json'])
            self.assertTrue(receipt['bundle_created'])
            package.assert_called_once()
            self.assertFalse(self.c._jobs)
            self.c.close('writer','A',token.generation,timeout=0)
            self.opened('B')
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_generation_stale'):
                adapter.ssh_package_verified('writer',token,'output.p01bundle',
                    'LAB-001','R1','NODE-01','network.json',['ssh.json'])
            package.assert_called_once()

    def test_private_ssh_export_requires_workspace_write_and_tracks_job(self):
        token=self.opened()
        adapter=self.adapter()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_access_denied'):
                adapter.ssh_export_verified('reader',token,directory,'lab',{'status':'collected'})
            self.assertEqual(list(Path(directory).iterdir()),[])
            result=adapter.ssh_export_verified('writer',token,directory,'lab',
                                               {'status':'collected'})
            self.assertEqual(result['workspace_id'],'A')
            self.assertEqual(result['generation'],token.generation)
            self.assertTrue((Path(directory)/result['filename']).is_file())
            self.assertFalse(self.c._jobs)
            self.c.close('writer','A',token.generation,timeout=0)
            self.opened('B')
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_generation_stale'):
                adapter.ssh_export_verified('writer',token,directory,'late',{})
            self.assertEqual(len(list(Path(directory).iterdir())),1)

    def test_verified_network_read_is_fenced_and_preserves_provenance(self):
        token=self.opened()
        adapter=self.adapter()
        projected={'observations':[{'source_asset_id':'asset-1','signals':[],
                                    'source_refs':[]}],'import':{}}
        with patch.object(adapter.sources,'prepare',return_value=projected) as source,patch(
                'P01_Observed_Network.project_verified_network_observations',
                return_value=[{'source_asset_id':'asset-1','kind':'ip',
                               'value':'192.0.2.10','source_paths':['network.json'],
                               'origin':'observed','graph_edges':[],
                               'ownership_confirmed':False}]) as projection:
            result=adapter.verified_network_observations('reader',token,'LAB-001',
                                                         'bnd-'+'a'*20)
            self.assertEqual(result['workspace_id'],'A')
            self.assertEqual(result['generation'],token.generation)
            self.assertEqual(result['observations'][0]['source_paths'],['network.json'])
            source.assert_called_once_with('A','LAB-001','bnd-'+'a'*20)
            projection.assert_called_once_with(projected)
            self.assertFalse(self.c._jobs)
            self.c.close('writer','A',token.generation,timeout=0)
            self.opened('B')
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_generation_stale'):
                adapter.verified_network_observations('reader',token,'LAB-001','bnd-'+'a'*20)
            source.assert_called_once()

    def test_subnet_candidates_use_only_persisted_workspace_evidence(self):
        token=self.opened()
        adapter=self.adapter()
        evidence={'revision':0,'observations':[
            {'kind':'ip','origin':'observed','source_asset_id':'asset-1',
             'value':'192.0.2.10','source_paths':['network.json']},
            {'kind':'mac','origin':'observed','source_asset_id':'asset-1',
             'value':'aa:bb:cc:dd:ee:ff','source_paths':['network.json']}]}
        with patch.object(model,'persisted_network_observations',
                          return_value=evidence) as read:
            result=adapter.observed_subnet_candidates('reader',token,prefix_length=24,
                                                      source_asset_id='asset-1')
            self.assertEqual(len(result['candidates']),1)
            self.assertEqual(result['candidates'][0]['candidate_subnet'],'192.0.2.0/24')
            self.assertIsNone(result['candidates'][0]['vlan_id'])
            self.assertEqual(result['candidates'][0]['graph_edges'],[])
            read.assert_called_once()
            self.assertFalse(self.c._jobs)
        with self.assertRaisesRegex(pg.PersistenceError,'workspace_input_invalid'):
            adapter.observed_subnet_candidates('reader',token,prefix_length=True)
        self.c.close('writer','A',token.generation,timeout=0)
        self.opened('B')
        with patch.object(model,'persisted_network_observations') as read:
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_generation_stale'):
                adapter.observed_subnet_candidates('reader',token,prefix_length=24)
            read.assert_not_called()

    def test_verified_interface_ref_rejected_before_projecting_untrusted_payload(self):
        token=self.opened()
        adapter=self.adapter()
        projection={'observations':[{'source_refs':[{'role':'credentialed_evidence',
                   'path':'trusted.json','sha256':'a'*64}]}]}
        evidence={'collection_status':'collected','network':{'interfaces':[]}}
        with patch.object(adapter.sources,'prepare',return_value=projection),patch(
                'P01_Observed_Interfaces.project_interfaces') as collector:
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_input_invalid'):
                adapter.verified_interface_observations('reader',token,'LAB-001',
                    'bnd-'+'a'*20,evidence,'forged.json','b'*64)
            collector.assert_not_called()
            receipt=adapter.verified_interface_observations('reader',token,'LAB-001',
                'bnd-'+'a'*20,evidence,'trusted.json','a'*64)
            self.assertEqual(receipt['workspace_id'],'A')
            collector.assert_called_once()
            self.assertFalse(self.c._jobs)

    def test_read_is_registered_and_postcheck_suppresses_revoked_result(self):
        token=self.opened();adapter=self.adapter()
        def read(*args,**kwargs):
            self.assertEqual(len(self.c._jobs),1);self.grants['reader'].clear();return {'objects':['private']}
        with patch.object(model,'list_objects',side_effect=read):
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_access_denied'):adapter.objects('reader',token)
        self.assertFalse(self.c._jobs)
    def test_write_denied_before_model_and_source_access(self):
        token=self.opened();adapter=self.adapter()
        with patch.object(model,'declare_object') as write,patch.object(adapter.sources,'prepare') as prepare:
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_access_denied'):
                adapter.declare_object('reader',token)
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_access_denied'):
                adapter.preview_import('reader',token,'LAB-001','bnd-'+'a'*20)
            write.assert_not_called();prepare.assert_not_called()
    def test_close_tracks_source_preparation_and_blocks_late_preview(self):
        token=self.opened();adapter=self.adapter();ready=threading.Event();release=threading.Event();errors=[]
        def prepare(*args):ready.set();self.assertTrue(release.wait(3));return {}
        def work():
            try:adapter.preview_import('writer',token,'LAB-001','bnd-'+'a'*20)
            except pg.PersistenceError as exc:errors.append(str(exc))
        with patch.object(adapter.sources,'prepare',side_effect=prepare),patch.object(model,'preview_import') as preview:
            worker=threading.Thread(target=work);worker.start();self.assertTrue(ready.wait(3))
            try:
                with self.assertRaisesRegex(pg.PersistenceError,'workspace_close_pending'):
                    self.c.close('writer','A',token.generation,timeout=0)
            finally:release.set();worker.join(3)
            self.assertFalse(worker.is_alive());preview.assert_not_called()
        self.assertEqual(errors,['workspace_generation_stale']);self.assertFalse(self.c._jobs)
        self.c.close('writer','A',self.c.generation,timeout=0)
    def test_ssh_identity_import_rejects_unqualified_source_without_sql(self):
        token=self.opened();adapter=self.adapter()
        projection={'observations':[{'source_refs':[{'role':'credentialed_evidence','path':'ssh-evidence.json'}],
                   'signals':[{'kind':'hostname','qualified':False,'sources':['ssh.json']}]}]}
        with patch.object(adapter.sources,'prepare',return_value=projection), \
             patch.object(model,'preview_import') as preview, \
             patch.object(model,'apply_import') as apply:
            with self.assertRaisesRegex(pg.PersistenceError,'model_input_invalid'):
                adapter.commit_verified_ssh_bundle('writer',token,'LAB-001',
                                                     'bnd-'+'a'*20,'ssh-negative')
            preview.assert_not_called();apply.assert_not_called()

    def test_ssh_identity_import_rejects_unrelated_fingerprint_provenance(self):
        token=self.opened();adapter=self.adapter()
        projection={'observations':[{
            'source_refs':[{'role':'credentialed_evidence','path':'ssh-evidence.json'}],
            'signals':[{'kind':'ssh_host_key_sha256','qualified':True,
                        'sources':['unrelated.json']}]}]}
        with patch.object(adapter.sources,'prepare',return_value=projection), \
             patch.object(model,'preview_import') as preview:
            with self.assertRaisesRegex(pg.PersistenceError,'model_input_invalid'):
                adapter.commit_verified_ssh_bundle('writer',token,'LAB-001',
                                                     'bnd-'+'a'*20,'ssh-unrelated')
            preview.assert_not_called()

    def test_ssh_identity_import_uses_verified_projection_and_model_fences(self):
        token=self.opened();adapter=self.adapter()
        projection={'observations':[{'source_refs':[{'role':'credentialed_evidence','path':'ssh-evidence.json'}],
                   'signals':[{'kind':'ssh_host_key_sha256','qualified':True,
                               'sources':['ssh-evidence.json']}]}]}
        with patch.object(adapter.sources,'prepare',return_value=projection), \
             patch.object(model,'preview_import',return_value={'plan_id':'plan-test'}) as preview, \
             patch.object(model,'apply_import',return_value={'status':'applied'}) as apply:
            result=adapter.commit_verified_ssh_bundle('writer',token,'LAB-001',
                                                       'bnd-'+'a'*20,'ssh-approved')
            self.assertEqual(result['qualified_ssh_observations'],1)
            self.assertEqual(result['workspace_id'],'A')
            self.assertEqual(result['generation'],token.generation)
            self.assertEqual(preview.call_args.kwargs['mode'],'evidence_only')
            apply.assert_called_once()

    def test_ssh_import_cancel_after_preview_prevents_apply(self):
        token=self.opened();adapter=self.adapter()
        projection={'observations':[{'source_refs':[{'role':'credentialed_evidence','path':'ssh.json'}],
                    'signals':[{'kind':'ssh_host_key_sha256','qualified':True,
                                'sources':['ssh.json']}]}]}
        started=threading.Event();release=threading.Event();errors=[]
        def delayed_preview(*args,**kwargs):
            started.set()
            self.assertTrue(release.wait(3))
            return {'plan_id':'plan-test'}
        def run():
            try:adapter.commit_verified_ssh_bundle('writer',token,'LAB-001',
                                                    'bnd-'+'a'*20,'ssh-cancel')
            except pg.PersistenceError as exc:errors.append(str(exc))
        with patch.object(adapter.sources,'prepare',return_value=projection), \
             patch.object(model,'preview_import',side_effect=delayed_preview), \
             patch.object(model,'apply_import') as apply:
            worker=threading.Thread(target=run);worker.start()
            self.assertTrue(started.wait(3))
            try:
                with self.assertRaisesRegex(pg.PersistenceError,'workspace_close_pending'):
                    self.c.close('writer','A',token.generation,timeout=0)
            finally:
                release.set();worker.join(3)
            self.assertFalse(worker.is_alive())
            self.assertEqual(errors,['workspace_generation_stale'])
            apply.assert_not_called()
        self.assertFalse(self.c._jobs)

    def test_ssh_import_revoked_write_blocks_before_evidence_io(self):
        token=self.opened();adapter=self.adapter()
        self.grants['writer'].discard(('A','workspace:write'))
        with patch.object(adapter.sources,'prepare') as prepare, \
             patch.object(model,'preview_import') as preview:
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_access_denied'):
                adapter.commit_verified_ssh_bundle('writer',token,'LAB-001',
                                                   'bnd-'+'a'*20,'ssh-revoked')
            prepare.assert_not_called()
            preview.assert_not_called()

    def test_old_token_rejected_before_reader(self):
        token=self.opened();self.c.close('writer','A',token.generation);self.opened('B')
        with patch.object(model,'list_objects') as read:
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_generation_stale'):self.adapter().objects('writer',token)
            read.assert_not_called()

@unittest.skipUnless(os.environ.get('CANCA_TEST_WORKSPACE_POSTGRES')=='1','workspace SQL opt-in required')
class ServicePostgreSQLTests(unittest.TestCase):
    setUp=models.ModelPostgreSQLTests.setUp
    legacy_rows=models.ModelPostgreSQLTests.legacy_rows
    role=models.ModelPostgreSQLTests.role
    create=models.ModelPostgreSQLTests.create
    source=models.ModelPostgreSQLTests.source
    def adapter(self):return service.WorkspaceService(self.c,service.SourceRoots({}))
    def test_service_reads_and_writes_with_exact_generation(self):
        with self.role('canca_ws_writer'):
            adapter=self.adapter();token=adapter.active_token(self.conn,'A',self.token.generation)
            result=adapter.declare_object(self.conn,token,0,'request','server','host','Server',reason='LAB')
            self.assertEqual(result['generation'],token.generation);self.assertEqual(result['revision'],1)
            inventory=adapter.objects(self.conn,token)
            self.assertEqual(inventory['objects'][0]['object_id'],'server')
            self.assertEqual(adapter.object(self.conn,token,'server')['metadata']['origin'],'declared')
            self.assertFalse(self.c._jobs)
    def test_active_registry_hides_other_workspace_id_and_inventory(self):
        with self.role('canca_ws_writer'):
            self.c.close(self.conn,'A',self.token.generation)
            self.c.open(self.conn,'B',self.c.generation)
        with self.role('canca_ws_a'):
            result=self.adapter().registry(self.conn)
            self.assertIsNone(result['lifecycle']['workspace_id'])
            self.assertEqual([w['workspace_id'] for w in result['workspaces']],['A'])
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_access_denied'):
                self.adapter().active_token(self.conn,'B',self.c.generation)
    def test_stale_generation_and_revoked_grants_never_return_inventory(self):
        with self.role('canca_ws_writer'):
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_generation_stale'):
                self.adapter().active_token(self.conn,'A',self.token.generation-1)
        service.ws.revoke_workspace(self.conn,'A','canca_ws_a','workspace:read')
        with self.role('canca_ws_a'):
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_access_denied'):
                self.adapter().objects(self.conn,self.token)
    def test_verified_source_preview_and_apply_are_registered(self):
        store,directory=assets.fixture(self.assetbase/'service')
        adapter=service.WorkspaceService(self.c,service.SourceRoots({'A':store}))
        with self.role('canca_ws_writer'):
            plan=adapter.preview_import(self.conn,self.token,'LAB-001',directory.name)
            self.assertEqual(plan['generation'],self.token.generation)
            result=adapter.apply_import(self.conn,self.token,plan['plan_id'],'apply-service')
            self.assertEqual(result['revision'],1);self.assertFalse(self.c._jobs)
    def test_atomic_verified_import_uses_existing_sql_fence(self):
        store,directory=assets.fixture(self.assetbase/'atomic-evidence')
        adapter=service.WorkspaceService(self.c,service.SourceRoots({'A':store}))
        with self.role('canca_ws_writer'):
            result=adapter.commit_verified_bundle(
                self.conn,self.token,'LAB-001',directory.name,'atomic-evidence-1')
            self.assertEqual(result['workspace_id'],'A')
            self.assertEqual(result['generation'],self.token.generation)
            self.assertEqual(result['status'],'applied')
            self.assertFalse(self.c._jobs)
            # Preview/apply are separate fenced transactions. Idempotent
            # apply with a stable plan is covered by the model contract.
            self.c.close(self.conn,'A',self.c.generation)
            self.c.open(self.conn,'B',self.c.generation)
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_generation_stale'):
                adapter.commit_verified_bundle(
                    self.conn,self.token,'LAB-001',directory.name,'atomic-evidence-stale')

    def test_real_ssh_fingerprint_reaches_workspace_sql_and_stale_token_is_rejected(self):
        base=self.assetbase/'ssh-real-model'
        base.mkdir(parents=True,exist_ok=True)
        network=assets.source.network_doc()
        network['assets'][0].update(ip='192.0.2.10',hostname='ssh.corp.example.test')
        network_path=assets.source.write_json(base/'network.json',network,sidecar=True)
        fingerprint='SHA256:'+base64.b64encode(bytes(range(32))).decode().rstrip('=')
        ssh_doc={
            'metadata':{'enricher_name':'P01-SSH-Credentialed-Enrichment',
                        'enricher_version':'0.4b.2.1',
                        'schema_version':'0.4b.2',
                        'secret_values_persisted_to_output':False},
            'target':{'ip':'192.0.2.10','port':22,'protocol':'ssh'},
            'authentication':{'success':True,
                              'server_host_key':{'fingerprint_sha256':fingerprint}},
            'enrichment':{'collection_status':'collected',
                          'identity':{'hostname':'ssh.corp.example.test'},
                          'network':{'interfaces':[],'routes':[]}},
        }
        target=assets.source.write_json(base/'P01-SSH-Enrichment_lab.json',ssh_doc,sidecar=True)
        manifest=assets.source.manifest_doc()
        manifest['assessment_id']='LAB-001'
        manifest_path=assets.source.write_json(base/'assessment.json',manifest)
        resolved=assets.registry.resolver.resolve(network_path,[target],manifest_path)
        resolved_path=assets.source.write_json(base/'resolved.json',resolved,sidecar=True)
        bundle=base/'ssh.p01bundle'
        assets.source.bundle_mod.create_bundle(
            bundle,'LAB-001','RUN-SSH','NODE-01',network_path,[target],
            manifest_path,resolved_path,require_evidence_sidecars=True)
        store=base/'store'
        imported=assets.source.mod.import_bundle(
            bundle,store,process=False,require_outer_sidecar=True)
        adapter=service.WorkspaceService(self.c,service.SourceRoots({'A':store}))
        directory=Path(imported['import_dir'])
        projection=adapter.sources.prepare('A','LAB-001',directory.name)
        fingerprint_signals=[
            signal for observation in projection['observations']
            for signal in observation['signals']
            if signal['kind']=='ssh_host_key_sha256']
        self.assertEqual(len(fingerprint_signals),1)
        self.assertEqual(fingerprint_signals[0]['value'],fingerprint)
        with self.role('canca_ws_writer'):
            result=adapter.commit_verified_ssh_bundle(
                self.conn,self.token,'LAB-001',directory.name,'ssh-model-integration')
            self.assertEqual(result['status'],'applied')
            self.assertEqual(result['qualified_ssh_observations'],1)
            # RLS requires the workspace-scoped transaction even for readback.
            with model.scope(self.conn,'A',self.token):
                rows=self.conn.execute(
                    "SELECT signals,source_refs FROM canca.workspace_observations "
                    "WHERE workspace_id='A'").fetchall()
            self.assertTrue(any(
                signal['kind']=='ssh_host_key_sha256' and signal['value']==fingerprint
                and any(ref['path'] in signal['sources'] for ref in refs)
                for signals,refs in rows for signal in signals))
            self.c.close(self.conn,'A',self.c.generation)
            b_token=self.c.open(self.conn,'B',self.c.generation)
            with model.scope(self.conn,'B',b_token):
                self.assertEqual(self.conn.execute(
                    'SELECT count(*) FROM canca.workspace_observations').fetchone()[0],0)
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_generation_stale'):
                adapter.commit_verified_ssh_bundle(
                    self.conn,self.token,'LAB-001',directory.name,'ssh-stale')

    def test_categories_real_sql_revision_and_role_isolation(self):
        adapter=self.adapter()
        self.create('server','host')
        self.create('switch','device')
        with self.role('canca_ws_a'):
            token=adapter.active_token(self.conn,'A',self.token.generation)
            compute=adapter.categories(self.conn,token,category='compute')
            self.assertEqual([x['object_id'] for x in compute['objects']],['server'])
            network=adapter.categories(self.conn,token,category='network',
                                       expected_revision=compute['revision'])
            self.assertEqual([x['object_id'] for x in network['objects']],['switch'])
            self.assertTrue(network['complete'])
            with self.assertRaisesRegex(pg.PersistenceError,'model_revision_stale'):
                adapter.categories(self.conn,token,category='network',
                                   expected_revision=compute['revision']-1)
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_access_denied'):
                adapter.categories(self.conn,runtime.Token('B',token.generation,token.lease_id),
                                   category='compute')
        service.ws.revoke_workspace(self.conn,'A','canca_ws_a','workspace:read')
        with self.role('canca_ws_a'):
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_access_denied'):
                adapter.categories(self.conn,self.token,category='network')

    def test_categories_switching_workspace_never_leaks_records(self):
        adapter=self.adapter()
        self.create('a-only','host')
        with self.role('canca_ws_writer'):
            self.c.close(self.conn,'A',self.token.generation)
            other=self.c.open(self.conn,'B',self.c.generation)
            result=adapter.categories(self.conn,other,category='compute')
            self.assertEqual(result['workspace_id'],'B')
            self.assertEqual(result['objects'],[])
            with self.assertRaisesRegex(pg.PersistenceError,'workspace_generation_stale'):
                adapter.categories(self.conn,self.token,category='compute')
        self.assertFalse(self.c._jobs)

    def test_connection_target_mismatch_rejected_before_sql(self):
        with patch.object(runtime,'connection_target',return_value=('other',5432,'other')):
            for call in (lambda:self.adapter().registry(self.conn),
                         lambda:self.adapter().active_token(self.conn,'A',self.token.generation)):
                with self.assertRaisesRegex(pg.PersistenceError,'workspace_connection_mismatch'):call()
