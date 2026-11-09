"""Fresh hosted Windows API transport retains all original actual-case checks."""
import ast
import copy
import json
from pathlib import Path
import sys
import unittest
import tempfile
import zipfile
import hashlib
from unittest.mock import patch
from contracts import ROOT
sys.path.insert(0,str(ROOT/'Tests/Production/GeneralApiCorrection/Hosted'))
import general_api_provider as provider
import general_api_worker as worker
import general_api_shaders as shaders
import prepare_general_api_data as data
import audit_hosted_general_api as audit
import execute_hosted_general_api as execution
import inactive_stager_fixture as fixture


def configuration():
    workspace='D:/a/orbiter-cross-platform/orbiter-cross-platform'
    paths={k:workspace+'/'+v for k,v in dict(source='application-source',preserved='out/current-windows-sdk/runtime',build='out/current-api-observer/Debug',data='out/current-stock-data',planets='out/current-stock-planets',mesa='out/current-stock-mesa',output='out/current-api-captures/Debug-GeneralApi',export='out/current-api-exports/Debug-GeneralApi').items()}
    roles={k:dict(commit=provider.APPLICATION if k!='runner' else 'f'*40,manifest_sha256='a'*64,
                  manifest_path=paths['preserved']+'/test-runtime.json' if k in ('application','sdk') else paths['build']+'/observer-build.json' if k=='observer' else workspace+'/out/current-api-requests/Debug-GeneralApi/runners.json')
           for k in ('application','sdk','observer','runner')}
    return dict(workspace=workspace,roots=paths,roles=roles,transport_protocol=provider.PROTOCOL,cohort='current-windows',source_role='application',source_commit=provider.APPLICATION,
        configuration='Debug',name='Debug-GeneralApi',math_profile='matrix',minimum_free_bytes=8*1024**3,
        capture_scope=dict(kind='diagnostic',gate='general-api',cases=['Scenarios/Tests/GeneralApiTest.scn']),
        github=dict(repository='dcajacob/orbiter-cross-platform',run_id=123,run_attempt=1,collector_commit='f'*40),
        variant=dict(manifest=workspace+'/out/current-api-variant/Debug-GeneralApi/variant.json',script=workspace+'/out/current-api-variant/Debug-GeneralApi/Script/Tests/GeneralApiTest.lua'),
        inactive_stager_fixture=dict(protocol=fixture.PROTOCOL,compiled_source=provider.APPLICATION,intended_module_enabled=False,sdk_manifest_sha256='a'*64,binary=workspace+'/out/current-stock-preparation/observer/ProductionCockpitDriver.dll',restoration_path=workspace+'/out/current-observer-restoration/restoration.json'),
        renderer_shader_delivery=dict(path=workspace+'/out/current-shader-delivery/Debug-GeneralApi.json',sha256='b'*64),**paths)


class HostedWindowsGeneralApiTests(unittest.TestCase):
    def test_all_original_simulator_loops_assertions_and_exports_are_conserved(self):
        old=worker.LEGACY.read_bytes().replace(b'\r\n',b'\n').decode();new=worker.prepared_body();ast.parse(new)
        original=old[old.index("        for profile in ('automatic','sse2'):"):old.index('    except BaseException')]
        actual=new[new.index("        for profile in ('automatic','sse2'):"):new.index('    except BaseException')]
        for addition in ("                        guards.update(stage_shader_inputs(directory,cfg))\n",
                         "                    inspect_shader_inputs(folder,cfg)\n",
                         "                        guards.update(stage_inactive_fixture(directory,cfg))\n",
                         "                        inspect_inactive_fixture(directory,cfg)\n",
                         "                    inspect_inactive_fixture(folder,cfg)\n",
                         "            paths += [folder/'Modules/Plugin/ProductionCockpitDriver.dll']\n",
                         "            paths += [p for p in (folder/'Modules/OGLClient').rglob('*') if p.is_file()]\n"):
            self.assertEqual(actual.count(addition),1);actual=actual.replace(addition,'',1)
        self.assertEqual(actual,original)
        self.assertIn('cloud_builds_used=True',new)
        self.assertNotIn('from windows_session_v1',new);self.assertNotIn("cfg['active_session']",new)

    def test_every_original_shader_byte_and_data_transport_guard_are_conserved(self):
        text=shaders.prepared_body().replace("PROTOCOL='phase6-current-GeneralApi-same-source-shader-inputs-v1'","PROTOCOL='phase6-current-same-source-renderer-shader-inputs-v1'").replace("cell==configuration+'-GeneralApi'","cell in {configuration+'-'+m+'-'+p for m in ('automatic','sse2') for p in ('stock','reload')}")
        self.assertEqual(text,shaders.ORIGINAL.read_bytes().replace(b'\r\n',b'\n').decode())
        text=data.prepared_body().replace("a.cell in {c+'-GeneralApi' for c in ('Debug','Release')}","a.cell in {c+'-'+m+'-'+phase for c in ('Debug','Release') for m in ('automatic','sse2') for phase in ('stock','reload')}")
        self.assertEqual(text,data.ORIGINAL.read_bytes().replace(b'\r\n',b'\n').decode())

    def test_old_vm_claims_partial_scope_mismatched_roles_and_overlapping_roots_are_rejected(self):
        cfg=configuration();provider.validate(cfg)
        for mutate in (lambda c:c.update(desktop='private'),lambda c:c.update(nonce='old-vm-claim'),
                       lambda c:c.update(math_profile='automatic'),lambda c:c.update(name='Debug-automatic-stock'),
                       lambda c:c['roles']['sdk'].update(commit='e'*40),lambda c:c['roles'].pop('runner'),
                       lambda c:c['github'].update(run_attempt=2),lambda c:c['github'].update(collector_commit='e'*40),
                       lambda c:c['capture_scope'].update(cases=[]),
                       lambda c:(c['roots'].update(output=c['source']),c.update(output=c['source'])),
                       lambda c:c['inactive_stager_fixture'].update(intended_module_enabled=True),
                       lambda c:c['inactive_stager_fixture'].update(sdk_manifest_sha256='f'*64),
                       lambda c:c['variant'].update(manifest='C:/outside/variant.json')):
            changed=copy.deepcopy(cfg);mutate(changed)
            with self.assertRaises(ValueError):provider.validate(changed)

    def test_real_worker_protocol_requires_all_eight_owned_cases_and_inherited_context(self):
        cfg=configuration();context=dict(actual_pid=77,inherited_context_only=True,window_station='inherited-station',desktop='inherited-desktop')
        result=dict(status='captured-current-Windows-original-and-corrected-api-diagnostic-only',actual_processes=8,observer_equivalence=True,owning_runtime_sdk_provider_unchanged=True,
            transport_protocol=cfg['transport_protocol'],source=cfg['source_commit'],roles=cfg['roles'],configuration='Debug',math_profile='matrix',request_sha256='r',script_sha256='w',
            cloud_builds_used=True,diagnostic_only=True,native_admission_qualified=False,phase6_complete=False,context=context,
            root_preflight=dict(status='passed-actual-inherited-GitHub-Windows-GeneralApi-preflight',protocol=cfg['transport_protocol'],actual_context=context,no_VM_or_private_desktop_setup_used=True),
            cases={m+'-'+t+'-'+o:dict(process=dict(actual_returncode=0,timed_out=False,actual_pid=100,timeout_seconds=900))
                   for m in ('automatic','sse2') for t in ('original','corrected') for o in ('off','on')})
        execution.terminal(cfg,result,77,'w','r')
        for mutate in (lambda r:r['cases'].pop(next(iter(r['cases']))),lambda r:r.update(actual_processes=7),
                       lambda r:r.update(cloud_builds_used=False),lambda r:r.update(phase6_complete=True),
                       lambda r:r['context'].update(inherited_context_only=False),
                       lambda r:r['cases']['automatic-original-off']['process'].update(timed_out=True),
                       lambda r:r['cases']['sse2-corrected-on']['process'].update(timeout_seconds=60)):
            changed=copy.deepcopy(result);mutate(changed)
            with self.assertRaises(ValueError):execution.terminal(cfg,changed,77,'w','r')

    def test_original_case_auditor_and_only_standard_windows_jobs_remain_required(self):
        body=audit.LEGACY.read_bytes().replace(b'\r\n',b'\n').decode()
        start=body.index('    expected_script,unused=corrected(');end=body.index('    protected=',start)
        self.assertEqual(audit.original_case_body(),body[start:end])
        self.assertIn("timing['timeout_seconds']==900",audit.original_case_body())
        self.assertIn('dict(rendered_frames=60,successful_presents=60,context_deleted=True)',audit.original_case_body())
        workflow=(ROOT/'.github/workflows/phase6-current-windows-general-api.yml').read_text()
        self.assertEqual(workflow.count('runs-on: windows-2025'),1);self.assertEqual(workflow.count('runs-on: ubuntu-24.04'),1)
        self.assertIn('configuration: [Debug, Release]',workflow);self.assertIn('max-parallel: 2',workflow)
        self.assertIn('Controls.Test.py --lua /usr/bin/lua5.4',workflow)
        for forbidden in ('windows-2022','self-hosted:','continue-on-error','private_desktop_bootstrap'):
            self.assertNotIn(forbidden,workflow)


    def test_inactive_fixture_cannot_become_an_active_duplicate_or_missing_module(self):
        good='ACTIVE_MODULES\n  ProductionGeneralApiObserver\n  OGLClient\nEND_MODULES\n'
        self.assertEqual(set(fixture.inactive_configuration(good)),{'productiongeneralapiobserver','oglclient'})
        self.assertEqual(len(fixture.inactive_configuration(good+'; ProductionCockpitDriver\n')),2)
        for text in (good.replace('  OGLClient','  ProductionCockpitDriver'),
                     good.replace('END_MODULES','  productioncockpitdriver.DLL\nEND_MODULES'),
                     good.replace('END_MODULES','  OGLClient\nEND_MODULES'),
                     good.replace('ACTIVE_MODULES','MISSING_MODULES')):
            with self.assertRaises(ValueError):fixture.inactive_configuration(text)

    def test_actual_private_fixture_bytes_and_original_driver_hash_are_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'original.dll';source.write_bytes(b'disposable exact original fixture bytes')
            target=root/'case';target.mkdir();body='ACTIVE_MODULES\nProductionGeneralApiObserver\nOGLClient\nEND_MODULES\n'
            (target/'Orbiter.cfg').write_text(body)
            checksum=fixture.sha(source);cfg=dict(inactive_stager_fixture=dict(binary=str(source),sha256=checksum,intended_module_enabled=False))
            with patch.object(fixture,'guarded',return_value={str(source):checksum}):
                protected=fixture.stage(target,cfg)
                (target/'invocation.json').write_text(json.dumps(dict(driver_sha256=checksum)))
                result=fixture.verify_staged(target,cfg);self.assertFalse(result['module_enabled'])
                self.assertTrue(all(fixture.sha(path)==value for path,value in protected.items()))
                (target/fixture.NAME).write_bytes(b'wrong private fixture')
                with self.assertRaises(ValueError):fixture.verify_staged(target,cfg)
                self.assertEqual(source.read_bytes(),b'disposable exact original fixture bytes')


    def test_complete_hosted_sdk_seal_includes_all_pristine_and_separately_linked_members(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);runtime=root/'runtime';runtime.mkdir();archive=root/'runtime.zip'
            pristine={n:('original-'+n).encode() for n in ('Orbiter.exe','Orbitersdk/lib/Orbiter.lib','Orbitersdk/lib/Orbitersdk.lib','Orbitersdk/include/Orbitersdk.h')}
            sealed=dict(source_commit=provider.APPLICATION,files={n:hashlib.sha256(v).hexdigest() for n,v in pristine.items()})
            manifest=json.dumps(sealed).encode();members=dict(pristine,**{'test-runtime.json':manifest,'Modules/Plugin/OGLClient.dll':b'actual separately linked original renderer','Modules/OGLClient/Licenses/notice.txt':b'original source notice'})
            for name,body in members.items():path=runtime/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
            with zipfile.ZipFile(archive,'w') as output:
                for name,body in members.items():output.writestr(name,body)
            checksum=hashlib.sha256(manifest).hexdigest()
            item=dict(sdk_manifest_sha256=checksum,runtime_files_sha256={n:hashlib.sha256(b).hexdigest() for n,b in members.items()})
            self.assertEqual(audit.inspect_hosted_sdk_members(archive,runtime,item,checksum)[1],sealed)
            for mutate in (lambda v:v['runtime_files_sha256'].pop('Modules/Plugin/OGLClient.dll'),
                           lambda v:v['runtime_files_sha256'].update(**{'Modules/Plugin/OGLClient.dll':'f'*64}),
                           lambda v:v['runtime_files_sha256'].update(**{'unmanifested.dll':'f'*64}),
                           lambda v:v.update(sdk_manifest_sha256='f'*64)):
                changed=copy.deepcopy(item);mutate(changed)
                with self.assertRaises(ValueError):audit.inspect_hosted_sdk_members(archive,runtime,changed,checksum)
            (runtime/'Modules/Plugin/OGLClient.dll').write_bytes(b'changed actual renderer')
            with self.assertRaises(ValueError):audit.inspect_hosted_sdk_members(archive,runtime,item,checksum)
        workflow=(ROOT/'.github/workflows/phase6-current-windows-general-api.yml').read_text()
        self.assertIn('out/current-api-observer/${{ env.CONFIGURATION }}/**',workflow)


if __name__=='__main__':unittest.main()
