"""No normal capture may be relabelled or substituted for a family persistence proof."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from contracts import ROOT
import hosted_family_persistence as family


class HostedFamilyPersistenceTests(unittest.TestCase):
    def config(self):
        reader=family.matrix.matrix.physical.persistence.bind_owner(ROOT,family.matrix.matrix.physical.writers.SOURCE)
        return reader.native.settings(reader.protocols.V2)

    def test_full_normal_scope_is_preserved_before_any_selected_projection(self):
        config=self.config();ids=[v['id'] for v in config['cases']];profile='Debug-automatic';phase='stock-writer'
        capture=dict(producer_commit=family.matrix.matrix.physical.writers.SOURCE,phase=phase,host='native-linux',
            runtime_source_commit=family.matrix.matrix.physical.writers.RUNTIME,runtime_role='normal',observer_delay_ms=120,
            process_receipts='owned-pid-start-argv-exit-v1',runtime_identity=dict(configuration='Debug',math_profile='automatic'),
            cases_requested=ids,cases={n:dict(runs=[{},{}]) for n in ids},repeats=2,frames=960,failures={},diagnostic_only=False,
            status='captured-awaiting-independent-persistence-audit',phase6_complete=False,native_admission_qualified=False)
        observed=dict(status='audited-native-phase-only',phase=phase,profile=profile,source_producer=capture['producer_commit'],
            runtime_source=capture['runtime_source_commit'],runtime_role='normal',observer_delay_ms=120,actual_processes=76,
            actual_presentations=72960,cases=copy.deepcopy(capture['cases']),owning_bytes_unchanged=True,diagnostic_only=False,
            phase6_complete=False,native_admission_qualified=False)
        before=copy.deepcopy((capture,observed));self.assertEqual([c['id'] for c in family.full_capture(capture,observed,profile,phase,config)],family.CASES)
        self.assertEqual((capture,observed),before)
        for mutate in (lambda c,o:c.update(diagnostic_only=True),lambda c,o:c.update(runtime_role='diagnostic'),
                       lambda c,o:c['cases'].pop(ids[-1]),lambda c,o:o.update(actual_processes=18),
                       lambda c,o:c.update(frames=959),lambda c,o:o.update(phase6_complete=True)):
            c,o=copy.deepcopy((capture,observed));mutate(c,o)
            with self.assertRaises(ValueError):family.full_capture(c,o,profile,phase,config)

    def test_actual_source_process_start_argv_exit_and_all_frames_remain_required(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);argv=['/actual/orbiter-production','--save','actual.scn']
            invocation=dict(argv=argv,collector_producer_commit='a'*40,persistence_phase='stock-writer',runtime_role='normal')
            receipt=dict(terminal=True,cancelled=False,actual_returncode=0,actual_collector_pid=123,
                owned_process_identities=[dict(pid=123,start_ticks=456,argv=argv)])
            def write(r):
                (folder/'invocation.json').write_text(json.dumps(invocation));(folder/'process-receipt.json').write_text(json.dumps(r))
            observed=dict(lifecycle=dict(rendered_frames=960,successful_presents=960,context_deleted=True));write(receipt)
            self.assertEqual(family.process_identity(folder,'a'*40,'stock-writer',observed)['start_ticks'],456)
            for mutate in (lambda r:r.update(cancelled=True),lambda r:r.update(actual_returncode=1),
                           lambda r:r['owned_process_identities'][0].update(start_ticks=0),
                           lambda r:r['owned_process_identities'][0].update(argv=['other'])):
                r=copy.deepcopy(receipt);mutate(r);write(r)
                with self.assertRaises(ValueError):family.process_identity(folder,'a'*40,'stock-writer',observed)
            write(receipt)
            with self.assertRaises(ValueError):family.process_identity(folder,'b'*40,'stock-writer',observed)
            observed['lifecycle']['successful_presents']=959
            with self.assertRaises(ValueError):family.process_identity(folder,'a'*40,'stock-writer',observed)

    def test_both_actual_reloads_must_consume_the_same_untouched_Windows_parent_save(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);native=base/'native';windows=base/'windows';parent=base/'parent';entry='Scenarios/derived.scn'
            for directory,leaf in [(native,entry),(windows,entry),(parent,'Scenarios/(Current state).scn')]:
                p=directory/leaf;p.parent.mkdir(parents=True);p.write_bytes(b'exact saved scenario bytes\n')
            digest=family.sha(parent/'Scenarios/(Current state).scn');descriptor=dict(saved_input_sha256=digest)
            self.assertEqual(family.original_saved_input(native,windows,parent,descriptor,descriptor,dict(scenario_entry_point=entry)),digest)
            for directory,leaf in [(native,entry),(windows,entry),(parent,'Scenarios/(Current state).scn')]:
                p=directory/leaf;old=p.read_bytes();p.write_bytes(old+b'changed')
                with self.assertRaises(ValueError):family.original_saved_input(native,windows,parent,descriptor,descriptor,dict(scenario_entry_point=entry))
                p.write_bytes(old)
            with self.assertRaises(ValueError):family.original_saved_input(native,windows,parent,dict(saved_input_sha256='0'*64),descriptor,dict(scenario_entry_point=entry))

    def test_only_original_cases_readers_scalar_and_bounded_hosted_jobs_are_declared(self):
        self.assertEqual(family.CASES,family.original_family.CASES);self.assertEqual(len(family.family_cases(self.config())),9)
        self.assertTrue(family.source_binding.original_sources())
        source=(ROOT/'Tests/Production/Closeout/hosted_family_persistence.py').read_text()
        for required in ['physical.persistence.compare_pair','physical.persistence.serialization_calibration','matrix.bind_raw',
                         'physical.bound_native_tree','matrix.scalar_binding','reader.inspect_save','matrix.compare_reference']:
            self.assertIn(required,source)
        workflow=(ROOT/'.github/workflows/phase6-native-family-persistence.yml').read_text()
        self.assertIn('runs-on: ubuntu-24.04',workflow);self.assertIn('max-parallel: 2',workflow)
        self.assertIn('phase: [stock-writer, windows-save-reload]',workflow)
        self.assertNotIn('capture_native.py --',workflow);self.assertNotIn('cmake --build',workflow)
