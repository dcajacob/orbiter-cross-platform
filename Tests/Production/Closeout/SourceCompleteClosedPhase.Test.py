"""Source-complete receipt inspection rejects old cohorts and preserves all prior collection guards."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from contracts import ROOT
sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
import inspect_source_complete_phase as closed
import source_complete_provider as provider


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


prior=module('prior_source_complete_closed_fixture',ROOT/'Tests/Production/Closeout/HostedClosedPhase.Test.py')
reference=module('current_source_complete_reference_fixture',ROOT/'Tests/Production/Closeout/SourceCompleteCurrent.Test.py')


class SourceCompleteClosedPhaseTests(unittest.TestCase):
    def api(self):
        run=dict(id=123,repository=dict(full_name='dcajacob/orbiter-cross-platform'),head_sha=closed.CAPTURE,
            head_branch='qualification/current-stock-capture-v2',path='.github/workflows/phase6-current-source-complete-stock.yml',
            run_attempt=1,status='completed',conclusion='success')
        jobs=[dict(id=n+1,name='Source-complete current stock '+' '.join(cell),run_id=123,head_sha=closed.CAPTURE,
            status='completed',conclusion='success',labels=['windows-2025'],
            steps=[dict(name=name,status='completed',conclusion='success') for name in closed.REQUIRED_STEPS])
            for n,cell in enumerate(sorted(closed.EXPECTED))]
        jobs.append(dict(id=9,name='readiness',run_id=123,head_sha=closed.CAPTURE,status='completed',conclusion='success',
            labels=['ubuntu-24.04'],steps=[dict(name='Require the complete successful immutable independent original audit',status='completed',conclusion='success')]))
        return dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),run=run,jobs=jobs,
            artifact=dict(id=456,name='source-complete-current-stock-Debug-automatic-stock',expired=False,size_in_bytes=100,
                digest='sha256:'+'a'*64,workflow_run=dict(id=123,head_sha=closed.CAPTURE)))

    def test_actual_new_capture_namespace_and_full_readiness_are_required(self):
        record=self.api();cell=('Debug','automatic','stock');closed.api_identity(record,cell)
        for change in (lambda r:r['run'].update(head_sha='5b4a3f74f9242323151a71dac79f4aa41d740969'),
                       lambda r:r['run'].update(head_branch='qualification/current-stock-capture-v1'),
                       lambda r:r['run'].update(path='.github/workflows/phase6-current-stock.yml'),
                       lambda r:r['run'].update(status='in_progress'),lambda r:r['run'].update(conclusion='failure'),
                       lambda r:r['artifact'].update(name='current-stock-Debug-automatic-stock'),
                       lambda r:r['jobs'].pop(),lambda r:r['jobs'][-1]['steps'][0].update(conclusion='skipped'),
                       lambda r:r['jobs'][0]['steps'][0].update(conclusion='skipped'),
                       lambda r:r['jobs'][0].update(labels=['self-hosted'])):
            changed=copy.deepcopy(record);change(changed)
            with self.assertRaises(ValueError):closed.api_identity(changed,cell)

    def test_actual_new_collector_closure_preserves_every_source_guard(self):
        original=prior.closed
        try:
            prior.closed=closed
            prior.HostedClosedPhaseTests().test_collector_requires_the_actual_complete_immutable_source_closure()
        finally:prior.closed=original

    def test_actual_raw_process_checks_still_reject_replays_changed_exits_and_missing_repeats(self):
        original=prior.closed
        try:
            prior.closed=closed
            prior.HostedClosedPhaseTests().test_raw_process_receipts_reject_replayed_path_or_changed_exit_and_missing_repetition()
        finally:prior.closed=original

    def test_independent_original_receipts_resolve_exact_api_members_without_rewriting_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'fixture';source.mkdir();cfg=reference.SourceCompleteCurrentTests().receipts(source)
            expected=provider.reference_receipts(cfg);cfg['workspace']='D:/a/project';payload=root/'api-decoded';payload.mkdir()
            names=dict(reference_transport='original-stock-audit/transport/download.json',
                reference_audit='original-stock-audit/independent/writer-audit.json',
                reference_persistence_audit='original-stock-audit/independent/original-persistence-audit.json',
                reference_restoration='reference-audit-restoration/restoration.json')
            for name,relative in names.items():
                target=payload/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(cfg[name]['path'],target)
                cfg[name]=dict(cfg[name],path=cfg['workspace']+'/out/'+relative)
            original=copy.deepcopy(cfg);proof=dict(source_complete_reference=expected)
            self.assertEqual(closed.inspect_reference(payload,cfg,proof),expected);self.assertEqual(cfg,original)
            changed=copy.deepcopy(cfg);changed['reference_transport']['path']='D:/a/project/out/relabelled/download.json'
            with self.assertRaises(ValueError):closed.inspect_reference(payload,changed,proof)
            changed=copy.deepcopy(proof);changed['source_complete_reference']['original_auditor_source']='9af22bbd320b54025e9345f6bfbd05260d2287e8'
            with self.assertRaises(ValueError):closed.inspect_reference(payload,cfg,changed)
            path=payload/names['reference_persistence_audit'];path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaises(ValueError):closed.inspect_reference(payload,cfg,proof)

    def test_old_api_source_staging_process_export_and_terminal_bodies_are_conserved(self):
        old=(ROOT/'Tests/Production/CurrentWindows/Hosted/inspect_closed_phase.py').read_text()
        new=Path(closed.__file__).read_text().split('\n\ndef inspect_reference(payload,cfg,preflight):',1)[0]
        changes=[('from source_complete_provider import require,sha,validate,selection,reference_receipts','from provider import require,sha,validate,selection'),
            ('from execute_source_complete_phase import terminal','from execute_phase import terminal'),
            (closed.CAPTURE,'5b4a3f74f9242323151a71dac79f4aa41d740969'),
            ('qualification/current-stock-capture-v2','qualification/current-stock-capture-v1'),
            ('.github/workflows/phase6-current-source-complete-stock.yml','.github/workflows/phase6-current-stock.yml'),
            ("'Source-complete current stock '","'Current stock '"),
            ("artifact['name']=='source-complete-current-stock-'","artifact['name']=='current-stock-'"),
            ("files['Tests/Production/CurrentWindows/Hosted/source_complete_worker.py']","files['Tests/Production/CurrentWindows/Hosted/worker.py']"),
            ('phase6-independent-source-complete-current-closed-phase-v2','phase6-independent-current-closed-phase-v1'),
            ('bound-source-complete-current-API-source-process-and-raw-export-receipts-only','bound-current-API-source-process-and-raw-export-receipts-only'),
            ('    reference=inspect_reference(payload,cfg,preflight)\n',''),
            ('staging=staging,source_complete_reference=reference,','staging=staging,')]
        for before,after in changes:self.assertGreaterEqual(new.count(before),1);new=new.replace(before,after)
        added="""        if job['name']=='readiness':
            gate=[step for step in job['steps'] if step['name']=='Require the complete successful immutable independent original audit']
            require(len(gate)==1 and gate[0]['status']=='completed' and gate[0]['conclusion']=='success',
                    'Actual successful source-complete original audit readiness gate required')
            continue"""
        self.assertEqual(new.count(added),1);new=new.replace(added,"        if job['name']=='readiness':continue",1)
        self.assertEqual(ast.dump(ast.parse(new)),ast.dump(ast.parse(old)))


if __name__=='__main__':unittest.main()
