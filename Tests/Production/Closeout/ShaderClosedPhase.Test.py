"""The new closed reader binds actual API identity, unchanged processes and exact C08 shaders."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from contracts import ROOT

HOSTED=ROOT/'Tests/Production/CurrentWindows/Hosted';sys.path.insert(0,str(HOSTED))
import inspect_source_complete_shader_phase as closed
import inspect_current_shader_inputs as shaders
import inspect_source_complete_phase as old_closed
import source_complete_shader_provider as provider

def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

prior=module('shader_closed_old_fixtures',ROOT/'Tests/Production/Closeout/SourceCompleteClosedPhase.Test.py')
retry=module('shader_closed_retry_fixture',ROOT/'Tests/Production/Closeout/CurrentAuditRetry.Test.py')
delivery=module('shader_closed_delivery_fixture',ROOT/'Tests/Production/Closeout/CurrentShaderDelivery.Test.py')


class ShaderClosedPhaseTests(unittest.TestCase):
    def api(self):
        record=prior.SourceCompleteClosedPhaseTests().api();record['run'].update(id=closed.RUN,head_sha=closed.CAPTURE,
            head_branch='qualification/current-stock-capture-v4',path='.github/workflows/phase6-current-shader-stock.yml')
        for job in record['jobs']:
            job.update(run_id=closed.RUN,head_sha=closed.CAPTURE)
            if job['name']!='readiness':job['steps']=[dict(name=name,status='completed',conclusion='success') for name in closed.REQUIRED_STEPS]
        record['artifact'].update(name='shader-source-complete-current-stock-Debug-automatic-stock',workflow_run=dict(id=closed.RUN,head_sha=closed.CAPTURE))
        return record

    def test_exact_new_actual_run_source_namespace_and_all_original_steps_are_required(self):
        record=self.api();cell=('Debug','automatic','stock');closed.api_identity(record,cell)
        for change in (lambda r:r['run'].update(id=closed.RUN+1),lambda r:r['run'].update(run_attempt=2),
                       lambda r:r['run'].update(head_sha=old_closed.CAPTURE),lambda r:r['run'].update(head_branch='qualification/current-stock-capture-v3'),
                       lambda r:r['artifact'].update(name='retry-source-complete-current-stock-Debug-automatic-stock'),
                       lambda r:r['jobs'][0]['steps'][0].update(conclusion='skipped'),lambda r:r['jobs'].pop()):
            changed=copy.deepcopy(record);change(changed)
            with self.assertRaises(ValueError):closed.api_identity(changed,cell)

    def test_expanded_collector_source_closure_is_exact_and_preserves_all_original_sources(self):
        paths=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',closed.CAPTURE,'--','Tests/Production/CurrentWindows','Tests/Production/Closeout'],text=True).splitlines()
        files={name:hashlib.sha256(subprocess.check_output(['git','-C',str(ROOT),'show',closed.CAPTURE+':'+name]).replace(b'\r\n',b'\n')).hexdigest() for name in paths if name.endswith('.py')}
        manifest=dict(protocol='phase6-hosted-current-stock-runner-v1',commit=closed.CAPTURE,legacy_worker_sha256_lf='dddbbf40656524ffa2dddcfcd745767ed270d3d46109917c2da3a89f66a15c51',files_sha256=files)
        self.assertEqual(closed.collector_sources(manifest),files)
        changed=copy.deepcopy(manifest);changed['files_sha256'].pop('Tests/Production/CurrentWindows/Hosted/current_client_shaders.py')
        with self.assertRaises(ValueError):closed.collector_sources(changed)

    def test_raw_process_staging_and_terminal_contracts_remain_identical(self):
        def body(path,name):return ast.dump(next(n for n in ast.parse(Path(path).read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name==name),include_attributes=False)
        for name in ('process_receipts','inspect_staging'):self.assertEqual(body(closed.__file__,name),body(old_closed.__file__,name))
        original=prior.prior.closed
        try:
            prior.prior.closed=closed
            prior.prior.HostedClosedPhaseTests().test_raw_process_receipts_reject_replayed_path_or_changed_exit_and_missing_repetition()
        finally:prior.prior.closed=original

    def test_both_actual_retry_attempts_resolve_raw_retained_paths_without_rewriting_any_capture(self):
        with retry.CurrentAuditRetryTests().evidence() as (out,cfg,restored,manifest):
            expected=provider.reference_receipts(cfg);cfg['workspace']='D:/a/project'
            names=dict(reference_transport='original-stock-audit/transport/download.json',reference_audit='original-stock-audit/independent/writer-audit.json',
                reference_persistence_audit='original-stock-audit/independent/original-persistence-audit.json',reference_restoration='reference-audit-restoration/restoration.json')
            for name,relative in names.items():cfg[name]=dict(cfg[name],path=cfg['workspace']+'/out/'+relative)
            for relative,value in cfg['reference_retry_inputs'].items():value['path']=cfg['workspace']+'/out/'+relative
            before=copy.deepcopy(cfg);self.assertEqual(closed.inspect_reference(out,cfg,dict(source_complete_reference=expected)),expected);self.assertEqual(cfg,before)
            value=next(iter(cfg['reference_retry_inputs'].values()));value['path']='D:/outside/source.json'
            with self.assertRaises(ValueError):closed.inspect_reference(out,cfg,dict(source_complete_reference=expected))

    def test_independent_shader_source_checks_reject_coherent_byte_changes_and_missing_original_includes(self):
        with tempfile.TemporaryDirectory() as temporary:
            f=delivery.CurrentShaderDeliveryTests();owner,out,_,sdk,cfg,git=f.fixture(Path(temporary))
            with patch.object(delivery.assets.subprocess,'check_output',side_effect=git):
                plan=f.prepare(out,sdk,owner,cfg);guards=delivery.assets.load(sdk)['source_guard_sha256_lf'];source_checks,_=shaders.inspect_sources(plan,guards)
                self.assertEqual(set(source_checks),{v['source'] for v in plan['files'].values()})
                changed=copy.deepcopy(plan);changed['files']['Modules/OGLClient/Constellations.vs']['sha256']='a'*64
                with self.assertRaises(ValueError):shaders.inspect_sources(changed,guards)
                changed=copy.deepcopy(plan);changed['files'].pop('Modules/OGLClient/Common.inc')
                with self.assertRaises(ValueError):shaders.inspect_sources(changed,guards)


if __name__=='__main__':unittest.main()
