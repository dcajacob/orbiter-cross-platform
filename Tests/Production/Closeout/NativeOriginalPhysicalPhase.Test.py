"""Small scope/path/partial-result controls only; full hosted physical audits remain required."""
import ast
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from contracts import ROOT
import audit_native_original_phase as physical


class NativeOriginalPhysicalPhaseTests(unittest.TestCase):
    def scope(self,phase='stock-writer'):
        ids=['case%02d'%i for i in range(38)];cases={i:dict(runs=[{},{}]) for i in ids}
        capture=dict(producer_commit=physical.writers.SOURCE if phase=='stock-writer' else physical.reloads.SOURCE,
            phase=phase,host='native-linux',runtime_source_commit=physical.writers.RUNTIME,runtime_role='normal',
            observer_delay_ms=120,process_receipts='owned-pid-start-argv-exit-v1',runtime_identity=dict(configuration='Debug',math_profile='automatic'),
            cases_requested=ids,cases=cases,repeats=2,frames=960,failures={},diagnostic_only=False,
            status='captured-awaiting-independent-persistence-audit',phase6_complete=False,native_admission_qualified=False)
        observed=dict(status='audited-native-phase-only',phase=phase,profile='Debug-automatic',source_producer=capture['producer_commit'],
            runtime_source=physical.writers.RUNTIME,runtime_role='normal',observer_delay_ms=120,actual_processes=76,
            actual_presentations=76*960,cases=copy.deepcopy(cases),owning_bytes_unchanged=True,diagnostic_only=False,phase6_complete=False,native_admission_qualified=False)
        return capture,observed,dict(cases=[dict(id=i) for i in ids],frames=960)

    def test_both_phases_require_all_38_actual_cases_twice_and_all_76_recomputed_observations(self):
        for phase in ('stock-writer','windows-save-reload'):
            capture,observed,config=self.scope(phase)
            self.assertEqual(physical.complete_scope(capture,observed,'Debug-automatic',phase,config),config['cases'])
            for change in (lambda c,o:c.update(frames=959),lambda c,o:c['cases'].pop('case00'),lambda c,o:c['cases']['case00']['runs'].pop(),
                           lambda c,o:c.update(runtime_role='diagnostic'),lambda c,o:c.update(observer_delay_ms=0),
                           lambda c,o:c.update(producer_commit='a'*40),lambda c,o:o.update(actual_processes=75),
                           lambda c,o:o.update(actual_presentations=75*960),lambda c,o:o['cases'].pop('case00'),
                           lambda c,o:o.update(owning_bytes_unchanged=False),lambda c,o:o.update(phase6_complete=True)):
                c=copy.deepcopy(capture);o=copy.deepcopy(observed);change(c,o)
                with self.assertRaises(ValueError):physical.complete_scope(c,o,'Debug-automatic',phase,config)

    def test_retained_native_copy_cannot_change_a_byte_add_a_file_or_redirect_a_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);payload=root/'out/payload';source=payload/'native-stock-writer/Debug-automatic';source.mkdir(parents=True)
            target=root/'out/native-stock-writer/Debug-automatic';target.mkdir(parents=True)
            for directory in (source,target):(directory/'capture.json').write_bytes(b'{"fixture_only":true}')
            with patch.object(physical,'ROOT',root):
                self.assertEqual(set(physical.bound_native_tree(payload,target,'Debug-automatic','stock-writer')),{'capture.json'})
                (target/'capture.json').write_bytes(b'changed actual bytes')
                with self.assertRaises(ValueError):physical.bound_native_tree(payload,target,'Debug-automatic','stock-writer')
                (target/'capture.json').write_bytes((source/'capture.json').read_bytes());(target/'extra').write_bytes(b'unmanifested')
                with self.assertRaises(ValueError):physical.bound_native_tree(payload,target,'Debug-automatic','stock-writer')
                (target/'extra').unlink();(target/'redirect').symlink_to(source/'capture.json')
                with self.assertRaises(ValueError):physical.bound_native_tree(payload,target,'Debug-automatic','stock-writer')
                with self.assertRaises(ValueError):physical.bound_native_tree(payload,source,'Debug-automatic','stock-writer')

    def test_first_failure_is_preserved_in_a_fresh_separate_partial_report_without_runtime_credit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);out=root/'out';out.mkdir();api_file=out/'api.json';api_file.write_text('{}');scalar=out/'scalar.json';scalar.write_text('{}')
            output=out/'native-original-physical-audits/Debug-automatic-stock-writer.json'
            env=dict(GITHUB_ACTIONS='true',RUNNER_OS='Linux',GITHUB_REPOSITORY='dcajacob/orbiter-cross-platform',
                ImageOS='ubuntu24',GITHUB_WORKSPACE=str(root),GITHUB_SHA='a'*40)
            with patch.object(physical,'ROOT',root),patch.dict(os.environ,env),patch.object(physical.sys,'platform','linux'),\
                 patch.object(physical.subprocess,'check_output',side_effect=lambda argv,**kw:'a'*40+'\n' if 'rev-parse' in argv else ''),\
                 patch.object(physical.writers,'inspect',side_effect=ValueError('fixture-only raw receipt rejection')):
                with self.assertRaisesRegex(ValueError,'fixture-only raw receipt rejection'):
                    physical.inspect(out/'payload',{},out/'producer.zip',out/'native-stock-writer/Debug-automatic',
                        'Debug-automatic','stock-writer',scalar,out/'scalar.zip',out/'mesa',output,api_file)
            result=json.loads(output.read_text());self.assertEqual(result['status'],'failed')
            self.assertEqual(result['actual_native_processes'],0);self.assertEqual(result['actual_direct_original_native_pairs'],0)
            self.assertFalse(result['phase6_complete']);self.assertFalse(result['qualification_granted'])

    def test_dirty_auditor_source_cannot_begin_or_write_an_acceptance_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);output=root/'out/native-original-physical-audits/Debug-automatic-stock-writer.json'
            env=dict(GITHUB_ACTIONS='true',RUNNER_OS='Linux',GITHUB_REPOSITORY='dcajacob/orbiter-cross-platform',ImageOS='ubuntu24',GITHUB_WORKSPACE=str(root),GITHUB_SHA='a'*40)
            def git(argv,**kw):return 'a'*40+'\n' if 'rev-parse' in argv else ' M Tests/Production/RemainingStockPersistence/audit.py\n'
            with patch.object(physical,'ROOT',root),patch.dict(os.environ,env),patch.object(physical.sys,'platform','linux'),patch.object(physical.subprocess,'check_output',side_effect=git):
                with self.assertRaisesRegex(ValueError,'owning-source worktree'):
                    physical.inspect(None,None,None,None,'Debug-automatic','stock-writer',None,None,None,output,None)
            self.assertFalse(output.exists())

    def test_full_physical_auditor_cannot_start_as_a_local_fixture_or_execute_a_simulator(self):
        with patch.dict(os.environ,{'GITHUB_ACTIONS':'false'}):
            with self.assertRaisesRegex(ValueError,'standard hosted'):
                physical.inspect(None,None,None,None,None,None,None,None,None,None,None)
        tree=ast.parse(Path(physical.__file__).read_bytes())
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        self.assertFalse(any(n.func.attr in ('Popen','run','system','execv','execve') for n in calls))

    def test_all_original_comparison_and_observation_bodies_remain_exact_to_the_actual_capture_sources(self):
        import subprocess
        for name in ('audit.py','observations.py','capture_native.py'):
            path='Tests/Production/RemainingStockPersistence/'+name
            for producer in (physical.writers.SOURCE,physical.reloads.SOURCE):
                self.assertEqual((ROOT/path).read_bytes(),subprocess.check_output(['git','-C',str(ROOT),'show',producer+':'+path]))
        self.assertEqual(Path(physical.persistence.transport.__file__).resolve(),ROOT/'Tests/Production/RemainingStockPersistence/transport.py')
        tree=ast.parse(Path(physical.__file__).read_bytes());inspect=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='inspect')
        attrs={n.func.attr for n in ast.walk(inspect) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)}
        self.assertTrue({'compare_pair','serialization_calibration','inspect_native','inspect_windows'}<=attrs)


if __name__=='__main__':unittest.main()
