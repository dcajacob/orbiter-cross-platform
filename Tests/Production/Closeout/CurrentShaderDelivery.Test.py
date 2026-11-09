"""Small immutable shader/input fixtures, with every original simulation test retained."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from contracts import ROOT

HOSTED=ROOT/'Tests/Production/CurrentWindows/Hosted';sys.path.insert(0,str(HOSTED))
import current_client_shaders as assets
import prepare_current_data_retry as network
import source_complete_shader_worker as worker
import source_complete_retry_worker as old_worker
import execute_source_complete_shader_phase as execution
import execute_source_complete_retry_phase as old_execution
import source_complete_shader_provider as provider

def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

sdk_fixture=module('current_renderer_sdk_fixture',ROOT/'Tests/Production/Closeout/HostedWindowsSdk.Test.py')
scope_fixture=module('current_renderer_scope_fixture',ROOT/'Tests/Production/Closeout/HostedStockProvider.Test.py')


class CurrentShaderDeliveryTests(unittest.TestCase):
    def fixture(self,root):
        owner=root/'application-source';owner.mkdir();out=root/'out';runtime=out/'current-windows-sdk/runtime';runtime.mkdir(parents=True)
        files={'OVP/OGLClient/shaders/'+name:('original source '+name+'\n').encode() for name in assets.ESSENTIAL}
        files[assets.CMAKE]=b'file(GLOB shaders CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/shaders/*")\nCOMMAND ${CMAKE_COMMAND} -E copy_if_different ${shaders} "${ORBITER_TEST_RUNTIME}/Modules/OGLClient"\n'
        for name,body in files.items():
            p=owner/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
        (runtime/'Orbiter.exe').write_bytes(b'unmodified original executable fixture')
        manifest=runtime/'test-runtime.json';manifest.write_text(json.dumps(dict(source_commit=assets.PRODUCER,files={'Orbiter.exe':assets.sha(runtime/'Orbiter.exe')})))
        api=out/'current-sdk-source/api.json';api.parent.mkdir();api.write_bytes(b'unchanged verified SDK API fixture')
        sdk=out/'current-windows-sdk/restoration.json';ident,_,digest=assets.PINS['Debug']
        sdk.write_text(json.dumps(dict(protocol='phase6-github-current-sdk-restoration-v1',status='restored-and-verified-current-sdk-only',
            compiled_source=assets.PRODUCER,configuration='Debug',collector_source='e'*40,original_artifact_id=ident,original_artifact_sha256=digest,
            source_owner=str(owner),runtime=str(runtime),runtime_files_sha256={'test-runtime.json':assets.sha(manifest)},
            source_api_sha256=assets.sha(api),source_guard_sha256_lf={name:hashlib.sha256(body).hexdigest() for name,body in files.items()},
            stock_simulation_executed=False,phase6_complete=False,native_admission_qualified=False)))
        def git(argv,**kwargs):
            if 'rev-parse' in argv:return assets.PRODUCER+'\n'
            if 'ls-tree' in argv:return '\n'.join(sorted(n for n in files if n.startswith(assets.PREFIX)))+'\n'
            return files[argv[-1].split(':',1)[1]]
        cfg=dict(source=str(owner),source_commit=assets.PRODUCER,roles=dict(sdk=dict(commit=assets.PRODUCER,manifest_sha256=assets.sha(manifest))),
            github=dict(collector_commit='e'*40),configuration='Debug',name='Debug-sse2-stock')
        return owner,out,runtime,sdk,cfg,git

    def prepare(self,out,sdk,owner,cfg):
        plan=assets.build_plan(sdk,owner,'Debug','e'*40,cfg['name']);path=out/'current-shader-delivery'/(cfg['name']+'.json');path.parent.mkdir();path.write_text(json.dumps(plan))
        cfg['renderer_shader_delivery']=dict(path=str(path),sha256=assets.sha(path));return plan

    def test_all_original_shaders_and_includes_stage_and_export_without_changing_sdk_or_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            owner,out,runtime,sdk,cfg,git=self.fixture(Path(temporary));before={str(p):p.read_bytes() for p in [sdk,*runtime.rglob('*'),*owner.rglob('*')] if p.is_file()}
            with patch.object(assets.subprocess,'check_output',side_effect=git):
                plan=self.prepare(out,sdk,owner,cfg);verified=assets.verify(cfg);self.assertEqual(verified['actual_original_shader_and_include_count'],len(assets.ESSENTIAL))
                folder=out/'capture';folder.mkdir();guards=assets.stage(folder,cfg);self.assertEqual(len(guards),len(assets.ESSENTIAL)+1)
                receipt=assets.inspect_staged(folder,cfg);self.assertFalse(receipt['qualification_granted']);self.assertFalse(receipt['original_sdk_modified'])
                self.assertEqual({str(p):p.read_bytes() for p in map(Path,before)},before)
                (folder/'Modules/OGLClient/Constellations.vs').write_bytes(b'changed shader')
                with self.assertRaises(ValueError):assets.inspect_staged(folder,cfg)

    def test_source_tampering_missing_include_or_conflicting_shader_cannot_be_accepted(self):
        for mode in ('source','include','conflict'):
            with tempfile.TemporaryDirectory() as temporary:
                owner,out,_,sdk,cfg,git=self.fixture(Path(temporary))
                with patch.object(assets.subprocess,'check_output',side_effect=git):
                    self.prepare(out,sdk,owner,cfg);folder=out/'capture';folder.mkdir()
                    if mode=='source':(owner/'OVP/OGLClient/shaders/Constellations.vs').write_bytes(b'edited source')
                    elif mode=='include':(owner/'OVP/OGLClient/shaders/Common.inc').unlink()
                    else:
                        p=folder/'Modules/OGLClient/Constellations.vs';p.parent.mkdir(parents=True);p.write_bytes(b'old shader')
                    with self.assertRaises((ValueError,FileNotFoundError)):assets.stage(folder,cfg)

    def test_coherently_rehashed_delivery_plan_still_requires_the_original_source_and_all_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            owner,out,_,sdk,cfg,git=self.fixture(Path(temporary))
            with patch.object(assets.subprocess,'check_output',side_effect=git):
                plan=self.prepare(out,sdk,owner,cfg);plan['files'].pop('Modules/OGLClient/Common.inc')
                p=Path(cfg['renderer_shader_delivery']['path']);p.write_text(json.dumps(plan));cfg['renderer_shader_delivery']['sha256']=assets.sha(p)
                with self.assertRaises(ValueError):assets.verify(cfg)

    def test_future_sdk_retention_keeps_the_renderer_resource_directory_and_original_sdk_members(self):
        reader=sdk_fixture.reader
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);tested=root/'tested';tested.mkdir();sdk=sdk_fixture.HostedWindowsSdkTests().fixture(tested)
            archive=root/'sdk.zip'
            import zipfile
            with zipfile.ZipFile(archive,'w') as z:
                for name in [*sdk['files'],'test-runtime.json']:z.write(tested/name,name)
            original={name:(tested/name).read_bytes() for name in [*sdk['files'],'test-runtime.json']}
            resources={'Constellations.vs':b'actual immutable shader','Common.inc':b'actual immutable include','Licenses/notice.txt':b'actual renderer notice'}
            for name,body in resources.items():
                p=tested/'Modules/OGLClient'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
            reader.prepare_runtime(archive,tested,root/'retained',root/'variants','a'*40)
            for name,body in resources.items():self.assertEqual((root/'retained/Modules/OGLClient'/name).read_bytes(),body)
            for name,body in original.items():self.assertEqual((root/'retained'/name).read_bytes(),body)

    def test_worker_only_adds_asset_delivery_guards_and_raw_asset_exports_to_the_conserved_simulation(self):
        text=worker.prepared_body()
        self.assertEqual(text.count('stage_shader_inputs(directory,cfg)'),1);self.assertEqual(text.count('inspect_shader_inputs(folder,cfg)'),1)
        additions=[
            ("        guards[observer['binary']]=observer['sha256']\n        from current_client_shaders import guarded as shader_guarded,stage as stage_shader_inputs,inspect_staged as inspect_shader_inputs\n        guards.update(shader_guarded(cfg))","        guards[observer['binary']]=observer['sha256']"),
            ('                        def configure(directory):\n                            guards.update(stage_shader_inputs(directory,cfg))','                        def configure(directory):'),
            ("                            result=inspect_run(folder,executed,config,reader,cfg['source_commit'],source)\n                            inspect_shader_inputs(folder,cfg)","                            result=inspect_run(folder,executed,config,reader,cfg['source_commit'],source)"),
            ("        paths.extend(p for p in (folder/'Modules/OGLClient').rglob('*') if p.is_file())\n",'')]
        for before,after in additions:self.assertEqual(text.count(before),1);text=text.replace(before,after,1)
        self.assertEqual(text.replace('from source_complete_shader_provider import','from source_complete_retry_provider import'),old_worker.prepared_body())
        def body(path):return ast.dump(next(n for n in ast.parse(Path(path).read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='terminal'),include_attributes=False)
        self.assertEqual(body(execution.__file__),body(old_execution.__file__))

    def test_full_current_scope_and_exact_new_shader_plan_path_remain_mandatory(self):
        cfg,config=scope_fixture.HostedStockProviderTests().config();cfg.update(transport_protocol=provider.PROTOCOL,name='Debug-automatic-stock',reference_retry_inputs={
            'reference-api/audit.json':dict(path=cfg['workspace']+'/out/reference-api/audit.json',sha256='a'*64)},renderer_shader_delivery=dict(path=cfg['workspace']+'/out/current-shader-delivery/Debug-automatic-stock.json',sha256='b'*64))
        self.assertEqual(provider.selection(cfg,config),(config['cases'],False))
        cfg['renderer_shader_delivery']['path']='D:/outside/plan.json'
        with self.assertRaises(ValueError):provider.selection(cfg,config)


class OriginalDataTransportRetryTests(unittest.TestCase):
    def test_only_actual_HTTP504_retries_the_same_command_and_preserves_each_log_and_partial(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);helper=root/'helper';helper.write_bytes(b'original immutable helper');partial=root/'data.partial';partial.write_bytes(b'failed download bytes')
            responses=iter([SimpleNamespace(returncode=1,stdout='prepare_hosted_data.py\nurllib.error.HTTPError: HTTP Error 504: Gateway Time-out\n'),SimpleNamespace(returncode=0,stdout='all exact original files verified\n')]);calls=[];sleeps=[]
            def run(argv,**kwargs):calls.append(argv);return next(responses)
            result=network.run_preparation(['python','original-helper'],root/'attempts',{str(helper):network.sha(helper)},partial,run=run,sleep=sleeps.append)
            self.assertEqual(calls,[['python','original-helper']]*2);self.assertEqual(sleeps,[10]);self.assertEqual(len(result['attempts']),2)
            self.assertFalse(result['qualification_granted']);self.assertEqual((root/'attempts/attempt-1.partial').read_bytes(),b'failed download bytes')

    def test_hash_failure_never_retries_or_substitutes_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);helper=root/'helper';helper.write_bytes(b'original helper');calls=[]
            def run(argv,**kwargs):calls.append(argv);return SimpleNamespace(returncode=1,stdout='stock package SHA256 mismatch')
            with self.assertRaises(ValueError):network.run_preparation(['original'],root/'attempts',{str(helper):network.sha(helper)},run=run,sleep=lambda n:self.fail('must not retry a hash mismatch'))
            self.assertEqual(len(calls),1);result=json.loads((root/'attempts/transport.json').read_text());self.assertEqual(result['status'],'failed-original-data-preparation-unqualified')


if __name__=='__main__':unittest.main()
