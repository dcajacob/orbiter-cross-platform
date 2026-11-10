"""Publication cannot turn shortened, relabelled or substituted persistence evidence into a pass."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from contracts import ROOT
import verify_published_family_persistence as published


class PublishedFamilyPersistenceTests(unittest.TestCase):
    def test_every_completed_source_job_artifact_digest_and_standard_runner_is_required(self):
        original=json.loads((ROOT/'Tests/Production/Closeout/published-family-persistence-api.fixture.json').read_text())
        pin=published.load(published.LOCK)['cells']['automatic/stock-writer'];before=copy.deepcopy(original)
        published.closed.validate_api(original,pin);self.assertEqual(original,before)
        for mutate in (lambda r:r['jobs'].pop(),lambda r:r['jobs'][0].update(conclusion='failure'),
                       lambda r:r['jobs'][0].update(labels=['self-hosted']),lambda r:r['run'].update(status='in_progress'),
                       lambda r:r['run'].update(head_sha='0'*40),lambda r:r['artifact'].update(digest='sha256:'+'0'*64)):
            value=copy.deepcopy(original);mutate(value)
            with self.assertRaises(ValueError):published.closed.validate_api(value,pin)

    def test_every_profile_phase_case_repeat_frame_and_original_normal_scope_is_required(self):
        profiles={p+'/'+q:dict(profile=p,phase=q,actual_original_native_processes=18,actual_original_successful_presents=17280,
            cases=published.family.CASES,repeats=2,full_capture_normal_role_and_flags_preserved=True,
            original_comparisons_and_raw_member_bindings_verified=True) for p in published.PROFILES for q in published.PHASES}
        before=copy.deepcopy(profiles);result=published.full_cells(profiles);self.assertEqual(profiles,before)
        self.assertEqual(result['actual_original_native_processes'],144);self.assertEqual(result['passed_class_facets'],['persistence'])
        self.assertTrue(all(result[k] is False for k in published.family.FLAGS));first=next(iter(profiles))
        for mutate in (lambda p:p.pop(first),lambda p:p[first].update(repeats=1),lambda p:p[first].update(actual_original_native_processes=17),
                       lambda p:p[first].update(actual_original_successful_presents=17279),lambda p:p[first].update(cases=published.family.CASES[:-1]),
                       lambda p:p[first].update(full_capture_normal_role_and_flags_preserved=False),
                       lambda p:p[first].update(original_comparisons_and_raw_member_bindings_verified=False)):
            value=copy.deepcopy(profiles);mutate(value)
            with self.assertRaises(ValueError):published.full_cells(value)

    def test_exact_phase_owned_source_roster_and_published_witness_bytes_cannot_be_borrowed_or_dropped(self):
        relative='Tests/Production/Closeout/contracts.py';old=published.family.matrix.matrix.SOURCE;new=published.SOURCE
        historical=published.closed.gitsha(old,relative);current=published.closed.gitsha(new,relative)
        profile='Debug-automatic';phase='stock-writer';name='class-full-SDK-source-witnesses/family-persistence/'+profile+'/'+phase+'/'+relative
        body=published.family.subprocess.check_output(['git','-C',str(ROOT),'show',old+':'+relative])
        absolute=str(published.CI/relative);snapshot=str(published.CI/'out'/name)
        entry=dict(relative=relative,historical_source=old,historical_sha256=historical,current_source=new,current_sha256=current,
            immutable_historical_witness=snapshot,historical_report_rewritten=False,current_file_replaced=False)
        value=dict(profile=profile,phase=phase,historical_source_bindings={relative:entry,absolute:copy.deepcopy(entry)})
        prior=dict(report=dict(guarded_sources_sha256={relative:historical,absolute:historical}));bodies={name:body};guards={snapshot:historical,absolute:current}
        before=copy.deepcopy((value,prior,bodies,guards));self.assertEqual(published.source_witnesses(value,prior,new,bodies,guards),{name:historical});self.assertEqual((value,prior,bodies,guards),before)
        for mutate in (lambda v,p,b,g:v['historical_source_bindings'].pop(absolute),lambda v,p,b,g:b.update({name:body+b'changed'}),
                       lambda v,p,b,g:v['historical_source_bindings'][relative].update(historical_source=new),
                       lambda v,p,b,g:g.update({absolute:'0'*64})):
            v,p,b,g=copy.deepcopy((value,prior,bodies,guards));mutate(v,p,b,g)
            with self.assertRaises(ValueError):published.source_witnesses(v,p,new,b,g)

    def test_selected_process_files_preserve_the_full_source_owned_native_and_original_rosters(self):
        profile='Debug-automatic';phase='stock-writer';case='remaining_stock_018';folder=case+'-1';native='native-stock-writer/'+profile+'/'+folder+'/'
        reader=SimpleNamespace(windows=SimpleNamespace(shared=SimpleNamespace(TRACES=('state.csv',)),configuration_input=SimpleNamespace(SNAPSHOT='configuration-input.json')),protocols=SimpleNamespace(MARKER='frame.json'))
        executed=dict(scenario_entry_point='Scenarios/original.scn',playback_vessels=[]);observed=dict(executed_case=executed)
        config=dict(recording_files_sha256_lf={},delivery_repairs=[])
        leaves=['state.csv','stock-clock.csv','stock-vessel-complete.txt','scene.csv','scene.rgba','scene-summary.json','camera.csv',
            'renderer-info.json','graphics-lifecycle.json','renderer-modules.txt','invocation.json','mesa-bindings.json','math-profile.txt',
            'console.txt','Orbiter.log','Orbiter.cfg','process-result.json','reference-variant.json','actual-data-inputs.json',
            executed['scenario_entry_point'],'stock-step-clock.csv','frame.json','configuration-input.json','process-timing.json']
        original={'remaining-stock-repaired/'+folder+'/'+n:'a'*64 for n in leaves}
        raw=dict(raw_proof=dict(checked_retained_members_sha256={native+'native.csv':'b'*64,native+'invocation.json':'c'*64}),files_sha256={folder+'/native.csv':'b'*64,folder+'/invocation.json':'c'*64,folder+'/private/asset':'d'*64})
        result=published.selected_file_closure(profile,phase,case,1,observed,raw,original,config,reader)
        self.assertEqual(len(result),len(leaves)+2);self.assertNotIn(str(published.CI/'out/native-stock-writer'/profile/folder/'private/asset'),result)
        # Nested private assets retain their full raw-tree binding; they cannot be
        # relabelled as flat process evidence or silently replace actual outputs.
        value=copy.deepcopy(raw);value['files_sha256'][folder+'/native.csv']='0'*64
        with self.assertRaises(ValueError):published.selected_file_closure(profile,phase,case,1,observed,value,original,config,reader)
        changed=copy.deepcopy(original);changed.pop('remaining-stock-repaired/'+folder+'/invocation.json')
        with self.assertRaises(KeyError):published.selected_file_closure(profile,phase,case,1,observed,raw,changed,config,reader)
