"""Current capture keeps its complete simulation contract while requiring the fresh audited reference."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contracts import ROOT

HOSTED=ROOT/'Tests/Production/CurrentWindows/Hosted'
sys.path.insert(0,str(HOSTED))
import source_complete_provider as provider
import source_complete_worker as worker
import prepare_source_complete_request as request
import execute_source_complete_phase as execution
import source_complete_original_transport as transport


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


scope_fixture=module('source_complete_scope_fixture',ROOT/'Tests/Production/Closeout/HostedStockProvider.Test.py')
api_fixture=module('source_complete_api_fixture',ROOT/'Tests/Production/Closeout/SourceCompleteOriginal.Test.py')
reference_fixture=module('source_complete_receipts_fixture',ROOT/'Tests/Production/Closeout/SourceCompleteReference.Test.py')
phase_fixture=module('source_complete_phase_fixture',ROOT/'Tests/Production/Closeout/HostedStockPhase.Test.py')


class SourceCompleteCurrentTests(unittest.TestCase):
    def test_complete_scope_and_source_roles_cannot_inherit_the_old_transport(self):
        cfg,config=scope_fixture.HostedStockProviderTests().config();cfg['transport_protocol']=provider.PROTOCOL
        self.assertEqual(provider.selection(cfg,config),(config['cases'],False))
        for change in (lambda c:c.update(transport_protocol='phase6-github-current-stock-v2'),
                       lambda c:c.update(domain_uuid='vm-claim'),lambda c:c.update(desktop='private-claim'),
                       lambda c:c.update(scene_workers=2),lambda c:c['capture_scope']['cases'].pop(),
                       lambda c:c['roles']['sdk'].update(commit='d'*40)):
            changed=copy.deepcopy(cfg);change(changed)
            with self.assertRaises((ValueError,KeyError)):provider.selection(changed,config)

    def receipts(self,root,change=None):
        manifest,writer,cohort=reference_fixture.SourceCompleteReferenceTests().receipts()
        run,jobs=api_fixture.SourceCompleteOriginalTests().record();manifest['workflow_run']=transport.run_identity(run,jobs)
        restored=dict(protocol='phase6-source-complete-original-reference-restoration-v2',
            status='restored-exact-independently-audited-original-cohort-only',original_capture_source=request.ORIGINAL,
            original_auditor_source=request.AUDITOR,restorer_source='e'*40,original_windows_processes=608,
            original_api_archive_bindings={p:dict(fixture_only=True) for p in transport.legacy.PROFILES},
            original_saves_relabelled=False,current_or_native_qualification_granted=False,phase6_complete=False,native_admission_qualified=False)
        if change:change(manifest,writer,cohort,restored)
        names=('reference_transport','reference_audit','reference_persistence_audit','reference_restoration');values=(manifest,writer,cohort,restored)
        paths={name:root/(name+'.json') for name in names}
        def save(name,value):paths[name].write_text(json.dumps(value));return provider.sha(paths[name])
        msha=save(names[0],manifest);writer['download_manifest_sha256']=msha;wsha=save(names[1],writer)
        cohort.update(transport_sha256=msha,writer_audit_sha256=wsha);csha=save(names[2],cohort)
        restored.update(original_transport_sha256=msha,original_writer_audit_sha256=wsha,original_cohort_audit_sha256=csha);save(names[3],restored)
        return dict(roles=dict(runner=dict(commit='e'*40)),**{name:dict(path=str(paths[name]),sha256=provider.sha(paths[name])) for name in names})

    def test_full_audit_and_actual_source_provenance_are_bound_even_with_coherently_rehashed_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);cfg=self.receipts(root);result=provider.reference_receipts(cfg)
            self.assertEqual(result['original_capture_run_id'],42544579421);self.assertEqual(result['original_windows_processes'],608)
            self.assertFalse(result['current_or_native_qualification_granted'])
            for change in (lambda m,w,c,r:m.update(protocol='remaining-stock-hosted-campaign-transport-v1'),
                           lambda m,w,c,r:m.update(source_commit='f9bf6c7814965cd897f349f97890d9e005cbb66d'),
                           lambda m,w,c,r:m['workflow_run']['source_provenance_job']['steps'][0].update(conclusion='skipped'),
                           lambda m,w,c,r:c.update(actual_windows_processes=607),lambda m,w,c,r:c.update(reload_processes=0),
                           lambda m,w,c,r:c.update(build_pairs={'automatic':{}}),
                           lambda m,w,c,r:c.update(auditor_source='9af22bbd320b54025e9345f6bfbd05260d2287e8'),
                           lambda m,w,c,r:r.update(restorer_source='d'*40),lambda m,w,c,r:r.update(original_saves_relabelled=True),
                           lambda m,w,c,r:r.update(native_admission_qualified=True)):
                cfg=self.receipts(root,change)
                with self.assertRaises(ValueError):provider.reference_receipts(cfg)
            cfg=self.receipts(root);path=Path(cfg['reference_persistence_audit']['path']);path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaises(ValueError):provider.reference_receipts(cfg)

    def test_every_exact_original_save_still_requires_both_actual_repeats_and_source_identity(self):
        original=phase_fixture.request
        try:
            phase_fixture.request=request
            phase_fixture.HostedStockPhaseTests().test_saved_input_selection_retains_both_exact_repeats_for_every_original_case()
        finally:phase_fixture.request=original

    def test_terminal_results_still_require_all_real_successful_process_receipts(self):
        cfg,result=phase_fixture.HostedStockPhaseTests().worker();cfg['transport_protocol']=provider.PROTOCOL;result['transport_protocol']=provider.PROTOCOL
        execution.terminal(cfg,result,99,'b'*64,'a'*64)
        for change in (lambda r:r.update(actual_processes=75),lambda r:r.update(successful_presents=76*960-1),
                       lambda r:r['actual_process_receipts'][0]['timing'].update(actual_returncode=1),
                       lambda r:r['actual_process_receipts'][0]['timing'].update(timed_out=True),
                       lambda r:r['context'].update(actual_pid=100),lambda r:r.update(phase6_complete=True)):
            changed=copy.deepcopy(result);change(changed)
            with self.assertRaises(ValueError):execution.terminal(cfg,changed,99,'b'*64,'a'*64)

    def test_all_old_capture_export_worker_and_request_guards_are_conserved(self):
        old=(HOSTED/'provider.py').read_text();new=Path(provider.__file__).read_text().split('\n\ndef reference_receipts(cfg):',1)[0]
        changes=[(provider.PROTOCOL,'phase6-github-current-stock-v2'),
            ("('reference_transport','reference_audit','reference_persistence_audit','reference_restoration')","('reference_transport','reference_audit')"),
            ('remaining-stock-source-complete-hosted-transport-v2','remaining-stock-hosted-campaign-transport-v1'),
            ('    reference=reference_receipts(cfg)\n',''),(',\n        source_complete_reference=reference', '')]
        for a,b in changes:self.assertEqual(new.count(a),1);new=new.replace(a,b,1)
        self.assertEqual(ast.dump(ast.parse(old)),ast.dump(ast.parse(new)))
        old=(HOSTED/'worker.py').read_text();new=Path(worker.__file__).read_text()
        self.assertEqual(new.replace('from source_complete_provider import context,preflight,require,sha,selection','from provider import context,preflight,require,sha,selection',1),old)
        new_tree=ast.parse(worker.prepared_body());old_worker=scope_fixture.worker
        def lane(tree):return next(n for n in ast.walk(tree) if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='phase')
        self.assertEqual(ast.dump(ast.Module(lane(new_tree).body,type_ignores=[])),ast.dump(ast.Module(lane(ast.parse(old_worker.prepared_body())).body,type_ignores=[])))
        old=(HOSTED/'prepare_request.py').read_text();new=Path(request.__file__).read_text()
        for a,b in [('from source_complete_provider import PROTOCOL,require,sha,selection,validate,reference_receipts','from provider import PROTOCOL,require,sha,selection,validate'),
                    ('from restore_source_complete_reference import ORIGINAL,AUDITOR,audit_receipts','from restore_reference import ORIGINAL,AUDITOR,audit_receipts'),
                    ("    require(reference_restoration['protocol']=='phase6-source-complete-original-reference-restoration-v2' and\n            reference_restoration['status']==","    require(reference_restoration['status']=="),
                    (';selection(cfg,config);reference_receipts(cfg)',';selection(cfg,config)')]:
            self.assertEqual(new.count(a),1);new=new.replace(a,b,1)
        self.assertEqual(new,old)
        old=(HOSTED/'execute_phase.py').read_text();new=Path(execution.__file__).read_text()
        self.assertEqual(new.replace('from source_complete_provider import require,sha,validate','from provider import require,sha,validate',1).replace("with_name('source_complete_worker.py')","with_name('worker.py')",1),old)

    def test_new_workflow_keeps_all_eight_complete_cells_and_separate_current_application(self):
        old=(ROOT/'.github/workflows/phase6-current-stock.yml').read_text()
        new=(ROOT/'.github/workflows/phase6-current-source-complete-stock.yml').read_text()
        self.assertIn("branches: ['qualification/current-stock-capture-v2']",new)
        self.assertIn("originalJobs.length!==5",new)
        changes=[('name: Phase 6 Source Complete Current Windows Stock Phases','name: Phase 6 Current Windows Complete Stock Phases'),
            ('qualification/current-stock-capture-v2','qualification/current-stock-capture-v1'),
            ('group: phase6-current-stock-capture-v2-${{ github.ref }}','group: phase6-current-stock-capture-${{ github.ref }}'),
            ('qualification/original-source-audit-v2','qualification/original-stock-audit-v1'),
            ('.github/workflows/phase6-original-source-audit.yml','.github/workflows/phase6-original-stock-audit.yml'),
            ('a13bae582c7de0c9b6e2fd0c064b1a3ea12e85c7','9af22bbd320b54025e9345f6bfbd05260d2287e8'),
            ("a.name==='source-complete-original-stock-independent-audit'","a.name==='original-stock-independent-audit'"),
            ('const original_id = 42544579421;','const original_id = 42515116858;'),
            ('ba38a7efccb5f770e87add95f5e966aa40270756','f9bf6c7814965cd897f349f97890d9e005cbb66d'),
            ('name: Source-complete current stock ${{ matrix.configuration }}','name: Current stock ${{ matrix.configuration }}'),
            ('Tests/Production/CurrentWindows/Hosted/restore_source_complete_reference.py','Tests/Production/CurrentWindows/Hosted/restore_reference.py'),
            ('Tests/Production/CurrentWindows/Hosted/prepare_source_complete_request.py','Tests/Production/CurrentWindows/Hosted/prepare_request.py'),
            ('Tests/Production/CurrentWindows/Hosted/execute_source_complete_phase.py','Tests/Production/CurrentWindows/Hosted/execute_phase.py'),
            ('name: source-complete-current-stock-controls','name: current-stock-controls'),
            ('name: source-complete-current-stock-${{','name: current-stock-${{'),
            ('name: source-complete-current-stock-partial-${{','name: current-stock-partial-${{')]
        for before,after in changes:self.assertGreaterEqual(new.count(before),1);new=new.replace(before,after)
        before="            const originalJobs = await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id:original_id,per_page:100});"
        after="            const originalJobs = (await github.paginate(github.rest.actions.listJobsForWorkflowRun,{owner,repo,run_id:original_id,per_page:100})).filter(j=>j.name.startsWith('Original Windows complete stock and exact-save reloads / Matched-clock v2 original '));"
        self.assertEqual(new.count(before),1);new=new.replace(before,after,1)
        before="workflow_run.status!=='completed' || workflow_run.conclusion!=='success' || originalJobs.length!==5 || originalJobs.filter(j=>j.name.startsWith('Original Windows source-complete writer and exact-save reloads / Matched-clock v2 original ')).length!==4"
        after="workflow_run.status!=='completed' || originalJobs.length!==4"
        self.assertEqual(new.count(before),1);new=new.replace(before,after,1)
        self.assertEqual(new,old)


if __name__=='__main__':unittest.main()
