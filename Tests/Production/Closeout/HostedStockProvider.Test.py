"""Conserve the original stock simulation body and reject mixed hosted identities."""
import ast
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from contracts import ROOT


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


provider=module('hosted_stock_provider',ROOT/'Tests/Production/CurrentWindows/Hosted/provider.py')
worker=module('hosted_stock_worker',ROOT/'Tests/Production/CurrentWindows/Hosted/worker.py')
legacy=module('original_current_stock_scope',ROOT/'Tests/Production/CurrentWindows/stock.py')


class HostedStockProviderTests(unittest.TestCase):
    def config(self):
        workspace='D:/actions/orbiter';roots={name:workspace+'/out/'+name for name in provider.ROOT_NAMES}
        roots['source']=workspace+'/application-source'
        roles={name:dict(commit=('a' if name in ('application','sdk') else 'b')*40,
                        manifest_sha256='c'*64,manifest_path=(roots['preserved'] if name in ('application','sdk') else roots['build'] if name=='observer' else workspace+'/request')+'/manifest.json')
               for name in provider.ROLES}
        cases=[dict(id='remaining_stock_'+str(i).zfill(3)) for i in range(1,39)]
        cfg=dict(transport_protocol=provider.PROTOCOL,cohort='current-windows',source_role='application',
                 workspace=workspace,roots=roots,roles=roles,source_commit='a'*40,configuration='Debug',
                 math_profile='automatic',phase='stock',scene_workers=1,minimum_free_bytes=8*1024**3,
                 github=dict(repository=provider.REPOSITORY,run_id=123,run_attempt=1,collector_commit='b'*40),
                 capture_scope=dict(kind='complete',gate='remaining-stock',cases=[c['id'] for c in cases]),**roots)
        return cfg,dict(cases=cases,frames=960)

    def test_explicit_complete_single_lane(self):
        cfg,config=self.config();cases,diagnostic=provider.selection(cfg,config)
        self.assertEqual(cases,config['cases']);self.assertFalse(diagnostic)
        cfg['math_profile']='sse2';self.assertEqual(len(provider.selection(cfg,config)[0]),38)

    def test_mixed_unsafe_or_vm_identities_are_rejected(self):
        changes=(lambda c:c.update(phase='both'),lambda c:c.update(math_profile='matrix'),lambda c:c.update(scene_workers=2),
                 lambda c:c.update(minimum_free_bytes=1024**3),lambda c:c.update(source_commit='d'*40),
                 lambda c:c.update(domain_uuid='not-a-hosted-identity'),lambda c:c.update(desktop='claimed-private-desktop'),
                 lambda c:c['github'].update(repository='another/repository'),lambda c:c['github'].update(run_id=True),
                 lambda c:c['roles']['sdk'].update(commit='d'*40),lambda c:c['roles'].pop('observer'),
                 lambda c:c['roles']['observer'].update(manifest_path='C:/outside/manifest.json'),
                 lambda c:c['roots'].update(output=c['roots']['data']),lambda c:c['roots'].pop('mesa'),
                 lambda c:c.update(source='C:/outside'))
        for change in changes:
            cfg,_=self.config();change(cfg)
            with self.assertRaises((ValueError,KeyError)):provider.validate(cfg)
        for path in ('../relative','C:relative','//server/share/root','D:/root/../escape','D:/root/file:stream'):
            with self.assertRaises(ValueError):provider.local_path(path)

    def test_no_partial_diagnostic_or_short_clock_scope(self):
        for change in (lambda c,p:c['capture_scope'].update(kind='diagnostic'),
                       lambda c,p:c['capture_scope']['cases'].pop(),lambda c,p:c['capture_scope']['cases'].reverse(),
                       lambda c,p:p.update(frames=959),lambda c,p:p['cases'].pop()):
            cfg,config=self.config();change(cfg,config)
            with self.assertRaises(ValueError):provider.selection(cfg,config)

    def test_historical_matrix_selection_stays_strict(self):
        cfg,config=self.config()
        with self.assertRaises(ValueError):legacy.selection(cfg,config)
        cfg['math_profile']='matrix';self.assertEqual(len(legacy.selection(cfg,config)[0]),38)
        with self.assertRaises(ValueError):provider.selection(cfg,config)

    def test_every_physical_capture_export_and_comparison_statement_is_conserved(self):
        original=ast.parse(worker.LEGACY.read_text());hosted=ast.parse(worker.prepared_body())
        def lane(tree):return next(n for n in ast.walk(tree) if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='phase')
        self.assertEqual(ast.dump(ast.Module(lane(original).body,type_ignores=[])),ast.dump(ast.Module(lane(hosted).body,type_ignores=[])))
        def exported(tree):return next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='export_run')
        self.assertEqual(ast.dump(exported(original)),ast.dump(exported(hosted)))
        imports=[n.module for n in ast.walk(hosted) if isinstance(n,ast.ImportFrom)]
        self.assertNotIn('windows_session_v1',imports);self.assertNotIn('runtime_descriptor_v3',imports)
        self.assertIn('provider',imports)

    def test_both_phases_and_all_four_profiles_must_close_before_matrix_coverage(self):
        _,config=self.config();ids=[c['id'] for c in config['cases']];records=[]
        for configuration in ('Debug','Release'):
            for mode in ('automatic','sse2'):
                for phase in ('stock','reload'):
                    records.append(dict(configuration=configuration,math_profile=mode,captured_phase=phase,phase=phase,
                        transport_protocol=provider.PROTOCOL,status='captured-current-Windows-stock-phase-awaiting-independent-audit',
                        actual_processes=76,successful_presents=76*960,owning_sources_runtime_sdk_provider_and_saved_inputs_unchanged=True,
                        simulation_comparison_and_independent_audit_pending=True,phase6_complete=False,native_admission_qualified=False,
                        source='a'*40,cases={mode+'-'+phase+'-'+name:dict(runs=[{},{}]) for name in ids}))
        self.assertEqual(provider.complete_phase_matrix(records,ids)['actual_processes'],608)
        for change in (lambda r:r.pop(),lambda r:r.append(copy.deepcopy(r[0])),lambda r:r[0].update(actual_processes=75),
                       lambda r:r[0].update(source='c'*40),lambda r:r[0]['cases'].pop(next(iter(r[0]['cases']))),
                       lambda r:r[0].update(captured_phase='reload'),lambda r:r[0].update(phase6_complete=True)):
            changed=copy.deepcopy(records);change(changed)
            with self.assertRaises(ValueError):provider.complete_phase_matrix(changed,ids)

    def test_a_changed_legacy_worker_cannot_silently_enter_the_hosted_route(self):
        original=worker.LEGACY
        try:
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'changed.py';path.write_bytes(original.read_bytes()+b'\n# altered source\n');worker.LEGACY=path
                with self.assertRaises(ValueError):worker.prepared_body()
        finally:worker.LEGACY=original


if __name__=='__main__':unittest.main()
