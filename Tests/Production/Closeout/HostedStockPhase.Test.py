"""Hosted phase requests require all exact saves and all real process/repetition receipts."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contracts import ROOT
sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
import prepare_request as request
import execute_phase as execution


class HostedStockPhaseTests(unittest.TestCase):
    def test_saved_input_selection_retains_both_exact_repeats_for_every_original_case(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);ids=[f'{n:03d}_original' for n in range(38)];config=dict(frames=960,cases=[dict(id=name) for name in ids]);members={}
            capture=dict(producer_commit=request.ORIGINAL,configuration='Debug',math_profile='automatic',protocol='remaining-stock-matched-clock-v2',
                status='captured-awaiting-independent-audit',diagnostic_only=False,cases_requested=ids,cases={name:dict(runs=[{},{}]) for name in ids},failures={})
            for name in ids:
                for repeat in (1,2):
                    relative=name+'-'+str(repeat)+'/Scenarios/(Current state).scn';path=root/relative;path.parent.mkdir(parents=True)
                    path.write_bytes((name+': exact original save '+str(repeat)+'\r\n').encode())
                    members['remaining-stock-repaired/'+relative]=request.sha(path)
            manifest=root/'capture.json';manifest.write_text(json.dumps(capture));checksum=request.sha(manifest)
            result=request.paired_inputs(config,root,'Debug','automatic',checksum,members)
            self.assertEqual(len(result),76);self.assertEqual({(r['case'],r['repeat']) for r in result},{(name,n) for name in ids for n in (1,2)})
            self.assertTrue(all(request.sha(item['path'])==item['sha256'] and item['parent_capture_sha256']==checksum for item in result))
            saved=Path(result[-1]['path']);before=saved.read_bytes();saved.write_bytes(before+b'changed')
            with self.assertRaises(ValueError):request.paired_inputs(config,root,'Debug','automatic',checksum,members)
            saved.write_bytes(before)
            for change in (lambda c:c.update(math_profile='sse2'),lambda c:c['cases'].pop(ids[-1]),lambda c:c['cases'][ids[0]].update(runs=[{}]),
                           lambda c:c.update(producer_commit='fc3a3a300c60fd2386b28662839b24df084fad7f')):
                changed=copy.deepcopy(capture);change(changed);manifest.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):request.paired_inputs(config,root,'Debug','automatic',request.sha(manifest),members)
            manifest.write_text(json.dumps(capture));self.assertEqual(request.sha(manifest),checksum)

    def worker(self):
        ids=[f'{n:03d}_original' for n in range(38)]
        cfg=dict(capture_scope=dict(cases=ids),math_profile='automatic',phase='stock',configuration='Debug',
                 transport_protocol='phase6-github-current-stock-v2',source_commit=request.APPLICATION,roles=dict(application='immutable',sdk='immutable',observer='immutable',runner='immutable'))
        worker=dict(status='captured-current-Windows-stock-phase-awaiting-independent-audit',transport_protocol=cfg['transport_protocol'],
            configuration='Debug',math_profile='automatic',phase='stock',captured_phase='stock',source=cfg['source_commit'],roles=cfg['roles'],
            request_sha256='a'*64,script_sha256='b'*64,cloud_builds_used=True,diagnostic_only=False,cases_requested=ids,repeats=2,frames=960,
            actual_processes=76,successful_presents=76*960,owning_sources_runtime_sdk_provider_and_saved_inputs_unchanged=True,
            simulation_comparison_and_independent_audit_pending=True,native_admission_qualified=False,phase6_complete=False,
            context=dict(actual_pid=99,inherited_context_only=True,window_station='WinSta0',desktop='Default'),
            actual_process_receipts=[dict(case=name,repeat=n,phase='stock',math_profile='automatic',
                timing=dict(actual_pid=100+i*2+n,actual_returncode=0,timed_out=False)) for i,name in enumerate(ids) for n in (1,2)],
            cases={'automatic-stock-'+name:dict(runs=[{},{}]) for name in ids})
        return cfg,worker

    def test_terminal_status_cannot_hide_missing_or_failed_processes_or_source_roles(self):
        cfg,worker=self.worker();execution.terminal(cfg,worker,99,'b'*64,'a'*64)
        for change in (lambda w:w.update(actual_processes=75),lambda w:w.update(successful_presents=76*960-1),
                       lambda w:w.update(captured_phase='reload'),lambda w:w.update(source='f'*40),
                       lambda w:w.update(phase6_complete=True),lambda w:w.update(cloud_builds_used=False),
                       lambda w:w['context'].update(actual_pid=100),lambda w:w['actual_process_receipts'][0]['timing'].update(actual_returncode=1),
                       lambda w:w['actual_process_receipts'][0]['timing'].update(timed_out=True),
                       lambda w:w['actual_process_receipts'].pop(),lambda w:w['cases'].pop(next(iter(w['cases'])))):
            changed=copy.deepcopy(worker);change(changed)
            with self.assertRaises(ValueError):execution.terminal(cfg,changed,99,'b'*64,'a'*64)


if __name__=='__main__':unittest.main()
