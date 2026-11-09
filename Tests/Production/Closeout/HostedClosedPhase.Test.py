"""Reject substituted API/source/exit evidence before any physical qualification can proceed."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contracts import ROOT
sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
import inspect_closed_phase as closed


class HostedClosedPhaseTests(unittest.TestCase):
    def api(self):
        run=dict(id=123,repository=dict(full_name='dcajacob/orbiter-cross-platform'),head_sha=closed.CAPTURE,
            head_branch='qualification/current-stock-capture-v1',path='.github/workflows/phase6-current-stock.yml',
            run_attempt=1,status='completed',conclusion='success')
        jobs=[dict(id=n+1,name='Current stock '+' '.join(cell),run_id=123,head_sha=closed.CAPTURE,status='completed',conclusion='success',
                   labels=['windows-2025'],steps=[dict(name=name,status='completed',conclusion='success') for name in closed.REQUIRED_STEPS])
              for n,cell in enumerate(sorted(closed.EXPECTED))]
        jobs.append(dict(id=9,name='readiness',run_id=123,head_sha=closed.CAPTURE,status='completed',conclusion='success',labels=['ubuntu-24.04']))
        return dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),run=run,jobs=jobs,
            artifact=dict(id=456,name='current-stock-Debug-automatic-stock',expired=False,size_in_bytes=100,digest='sha256:'+'a'*64,
                workflow_run=dict(id=123,head_sha=closed.CAPTURE)))

    def test_api_rejects_incomplete_phase_matrix_relabelled_build_and_skipped_capture(self):
        record=self.api();cell=('Debug','automatic','stock');closed.api_identity(record,cell)
        for mutate in (lambda r:r['run'].update(head_sha=closed.APPLICATION),lambda r:r['run'].update(run_attempt=2),
                       lambda r:r['artifact'].update(name='current-stock-Debug-automatic-reload'),
                       lambda r:r['jobs'].pop(),lambda r:r['jobs'][-1].update(conclusion='failure'),
                       lambda r:r['jobs'][0]['steps'][0].update(conclusion='skipped'),
                       lambda r:r['jobs'][0].update(labels=['self-hosted'])):
            changed=copy.deepcopy(record);mutate(changed)
            with self.assertRaises(ValueError):closed.api_identity(changed,cell)

    def test_collector_requires_the_actual_complete_immutable_source_closure(self):
        paths=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',closed.CAPTURE,'--','Tests/Production/CurrentWindows'],text=True).splitlines()
        names={p for p in paths if p.endswith('.py')}|{'Tests/Production/Closeout/LocalVM/stock_runtime_worker_v3.py',
            'Tests/Production/Closeout/LocalVM/static_binary_link_staging_v2.py'}
        files={name:hashlib.sha256(subprocess.check_output(['git','-C',str(ROOT),'show',closed.CAPTURE+':'+name]).replace(b'\r\n',b'\n')).hexdigest()
               for name in names}
        record=dict(protocol='phase6-hosted-current-stock-runner-v1',commit=closed.CAPTURE,files_sha256=files,
                    legacy_worker_sha256_lf='dddbbf40656524ffa2dddcfcd745767ed270d3d46109917c2da3a89f66a15c51')
        self.assertEqual(closed.collector_sources(record),files)
        for mutate in (lambda r:r['files_sha256'].pop(next(iter(files))),
                       lambda r:r['files_sha256'].update({next(iter(files)):'0'*64}),lambda r:r.update(commit=closed.APPLICATION)):
            changed=copy.deepcopy(record);mutate(changed)
            with self.assertRaises(ValueError):closed.collector_sources(changed)

    def test_raw_process_receipts_reject_replayed_path_or_changed_exit_and_missing_repetition(self):
        ids=[f'case-{n:03}' for n in range(38)]
        cfg=dict(math_profile='sse2',phase='reload',output='D:/a/project/out/capture',capture_scope=dict(cases=ids))
        records=[]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for n,identity in enumerate(ids):
                for repeat in (1,2):
                    relative=f'sse2-reload/{identity}-{repeat}';folder=root/relative;folder.mkdir(parents=True)
                    timing=dict(actual_pid=100+n*2+repeat,actual_returncode=0,timed_out=False,timeout_seconds=900,elapsed_wall_ns=100)
                    (folder/'process-timing.json').write_text(json.dumps(timing))
                    records.append(dict(case=identity,repeat=repeat,math_profile='sse2',phase='reload',
                        folder=cfg['output']+'/'+relative,timing=timing))
            worker=dict(actual_process_receipts=records);self.assertEqual(closed.process_receipts(cfg,worker,root),76)
            for mutate in (lambda w:w['actual_process_receipts'].pop(),
                           lambda w:w['actual_process_receipts'][0].update(folder='D:/different/replayed-run'),
                           lambda w:w['actual_process_receipts'][0]['timing'].update(actual_returncode=1),
                           lambda w:w['actual_process_receipts'].append(copy.deepcopy(w['actual_process_receipts'][0]))):
                changed=copy.deepcopy(worker);mutate(changed)
                with self.assertRaises(ValueError):closed.process_receipts(cfg,changed,root)
            path=root/'sse2-reload/case-000-1/process-timing.json';timing=json.loads(path.read_text());timing['actual_pid']+=1;path.write_text(json.dumps(timing))
            with self.assertRaises(ValueError):closed.process_receipts(cfg,worker,root)

    def test_original_staging_checks_are_conserved_without_importing_vm_launch_code(self):
        original=subprocess.check_output(['git','-C',str(ROOT),'show',closed.CAPTURE+':Tests/Production/CurrentWindows/audit_stock.py'])
        actual=Path(closed.__file__).read_bytes()
        def body(source):
            return ast.dump(next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='inspect_staging'),include_attributes=False)
        self.assertEqual(body(actual),body(original))


if __name__=='__main__':unittest.main()
