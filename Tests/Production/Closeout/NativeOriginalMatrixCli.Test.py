"""Disposable hosted-route, raw-binding and complete proof-aggregation controls."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
import native_original_matrix_cli as cli


class NativeOriginalMatrixCliTests(unittest.TestCase):
    def pair_api(self,mode='automatic',phase='stock-writer',head='a'*40):
        names=['Direct native original builds '+m+' '+p for m,p in sorted(cli.PAIRS)]
        jobs=[dict(name=name,run_id=44,head_sha=head,run_attempt=1,status='completed',conclusion='success',labels=['ubuntu-24.04'],
            steps=[dict(name=n,status='completed',conclusion='success') for n in cli.PAIR_STEPS]) for name in names]
        jobs.append(dict(name='readiness',run_id=44,head_sha=head,run_attempt=1,status='completed',conclusion='success',labels=['ubuntu-24.04'],
            steps=[dict(name='Require every actual original native physical phase before comparison',status='completed',conclusion='success')]))
        jobs.append(dict(name='Independently close all eight phases and all four direct build proofs',status='in_progress'))
        return dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),
            run=dict(id=44,head_sha=head,run_attempt=1,head_branch=cli.BRANCH,path=cli.WORKFLOW,status='in_progress',
                repository=dict(full_name='dcajacob/orbiter-cross-platform',private=False)),jobs=jobs,
            artifact=dict(id=100,name='native-original-direct-build-'+mode+'-'+phase,expired=False,size_in_bytes=20,
                digest='sha256:'+'b'*64,workflow_run=dict(id=44,head_sha=head)))

    def test_plan_retains_all_immutable_capture_pins_without_starting_jobs_or_changing_sources(self):
        p=cli.plan();self.assertFalse(p['qualification_granted']);self.assertEqual(p['physical_source'],cli.matrix.SOURCE)
        self.assertEqual(p['cohorts']['stock-writer']['pins'],cli.matrix.physical.writers.PINS)
        self.assertEqual(p['cohorts']['windows-save-reload']['pins'],cli.matrix.physical.reloads.PINS)
        self.assertEqual(len(p['physical_jobs']),8)

    def test_local_context_cannot_start_any_heavy_audit_or_create_a_partial_report(self):
        with patch.dict(os.environ,{'GITHUB_ACTIONS':'false'}):
            with self.assertRaisesRegex(ValueError,'Standard hosted'):cli.direct_pairs('automatic','stock-writer',None)
            with self.assertRaisesRegex(ValueError,'Standard hosted'):cli.final_matrix(None)

    def test_actual_context_rejects_changed_workflow_or_downloader_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);calls=[]
            env=dict(GITHUB_ACTIONS='true',RUNNER_OS='Linux',ImageOS='ubuntu24',GITHUB_REPOSITORY='dcajacob/orbiter-cross-platform',GITHUB_WORKSPACE=str(root),GITHUB_SHA='a'*40)
            def git(argv,**kwargs):
                calls.append(argv);return 'a'*40+'\n' if 'rev-parse' in argv else ' M .github/workflows/phase6-native-original-matrix.yml\n'
            with patch.object(cli,'ROOT',root),patch.dict(os.environ,env),patch.object(cli.sys,'platform','linux'),patch.object(cli.subprocess,'check_output',side_effect=git):
                with self.assertRaisesRegex(ValueError,'Clean actual'):cli.context()
            self.assertIn('.github',calls[-1])

    def test_first_input_rejection_is_preserved_as_failed_partial_with_zero_comparison_credit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);output=root/'out/native-original-matrix-results/automatic-stock-writer.json'
            with patch.object(cli,'ROOT',root),patch.object(cli,'context',return_value='a'*40),\
                 patch.object(cli.matrix.physical.persistence,'bind_owner',side_effect=ValueError('fixture-only original reader rejection')):
                with self.assertRaisesRegex(ValueError,'fixture-only'):cli.direct_pairs('automatic','stock-writer',output)
            r=json.loads(output.read_text());self.assertEqual(r['status'],'failed');self.assertEqual(r['actual_native_build_pairs'],0)
            self.assertEqual(r['actual_original_build_pairs'],0);self.assertFalse(r['phase6_complete']);self.assertFalse(r['qualification_granted'])
            with patch.object(cli,'ROOT',root):
                with self.assertRaises(ValueError):cli.partial_output(output,'fixture','a'*40)
                with self.assertRaises(ValueError):cli.partial_output(root/'out/native-matrix-native-inputs/overwrite.json','fixture','a'*40)

    def test_raw_native_binding_rejects_changed_tree_capture_api_and_unmanifested_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);profile='Debug-automatic';phase='stock-writer';base=root/'out/native-matrix-native-inputs'/(profile+'-'+phase);base.mkdir(parents=True)
            (base/'producer.zip').write_bytes(b'disposable fixture archive');(base/'api.json').write_text(json.dumps(dict(artifact=dict(digest='sha256:'+'a'*64))))
            payload=root/'payload';native=payload/'native-stock-writer'/profile;native.mkdir(parents=True)
            (native/'capture.json').write_text('{"fixture_only":true}');(native/'scene.rgba').write_bytes(b'fixture frame')
            files={p.name:cli.sha(p) for p in native.iterdir()};raw=dict(status='fixture-only source proof')
            proof=dict(report=dict(raw_native_proof=raw,native_API_archive_sha256='sha256:'+'a'*64,native_decoded_tree_sha256=files,
                independent_native_observations=dict(capture_sha256=cli.sha(native/'capture.json'))))
            with patch.object(cli,'ROOT',root),patch.object(cli.matrix.physical.writers,'inspect',return_value=raw):
                actual,binding=cli.bind_raw(profile,phase,proof,payload,decode=False);self.assertEqual(actual,native);self.assertEqual(binding['files_sha256'],files)
                (native/'scene.rgba').write_bytes(b'changed fixture frame')
                with self.assertRaises(ValueError):cli.bind_raw(profile,phase,proof,payload,decode=False)
                (native/'scene.rgba').write_bytes(b'fixture frame');(native/'extra').write_bytes(b'unmanifested')
                with self.assertRaises(ValueError):cli.bind_raw(profile,phase,proof,payload,decode=False)
                (native/'extra').unlink();bad=copy.deepcopy(proof);bad['report']['independent_native_observations']['capture_sha256']='f'*64
                with self.assertRaises(ValueError):cli.bind_raw(profile,phase,bad,payload,decode=False)
                bad=copy.deepcopy(proof);bad['report']['native_API_archive_sha256']='sha256:'+'e'*64
                with self.assertRaises(ValueError):cli.bind_raw(profile,phase,bad,payload,decode=False)

    def test_pair_api_requires_all_actual_same_source_pair_jobs_but_preserves_active_final_run_status(self):
        record=self.pair_api();cli.pair_api(record,'a'*40,44,'automatic','stock-writer');self.assertEqual(record['run']['status'],'in_progress')
        for change in (lambda r:r['run'].update(run_attempt=2),lambda r:r['run'].update(head_sha='f'*40),
                       lambda r:r['jobs'][0].update(conclusion='failure'),lambda r:r['jobs'][0]['steps'][0].update(conclusion='skipped'),
                       lambda r:r['artifact'].update(expired=True),lambda r:r['jobs'][4].update(conclusion='failure')):
            bad=copy.deepcopy(record);change(bad)
            with self.assertRaises(ValueError):cli.pair_api(bad,'a'*40,44,'automatic','stock-writer')

    def test_final_raw_archive_route_requires_all_four_complete_pair_reports_and_rejects_bad_fullframe(self):
        for damage in (False,True):
            with tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);ids=['fixture%02d'%i for i in range(38)];head='a'*40
                config=dict(cases=[dict(id=i) for i in ids],frames=960,budgets=dict(position_m=1e-5),image_ssim_minimum=.98)
                aggregate=dict(status='fixture-only already independently checked eight-phase aggregate')
                for index,(mode,phase) in enumerate(sorted(cli.PAIRS)):
                    label=mode+'-'+phase;base=root/'out/native-matrix-pair-inputs'/label;base.mkdir(parents=True)
                    pair=dict(state={},camera={},ssim=1.0,detail_calibration_only={})
                    record=dict(protocol='phase6-direct-native-original-build-phase-v1',status='passed-one-complete-native-original-direct-build-phase-only',
                        auditor_source=head,math_profile=mode,phase=phase,required_cases=38,required_repeats=2,required_frames=960,
                        actual_native_build_pairs=76,actual_original_build_pairs=76,complete_phase_aggregation=aggregate,
                        unchanged_budgets=config['budgets'],unchanged_image_ssim_minimum=.98,
                        cases={i:dict(runs=[dict(native=copy.deepcopy(pair),original=copy.deepcopy(pair)) for j in range(2)]) for i in ids},
                        qualification_granted=False,phase6_complete=False,native_admission_qualified=False,full_four_pair_aggregation_pending=True,
                        current_native_comparisons_pending=True,other_class_lifetime_full157_and_hardware_gates_pending=True)
                    if damage and index==0:record['cases'][ids[0]]['runs'][0]['native']['ssim']=.979
                    archive=base/'producer.zip'
                    with zipfile.ZipFile(archive,'w') as out:out.writestr('native-original-matrix-results/'+label+'.json',json.dumps(record))
                    api=self.pair_api(mode,phase,head);api['artifact'].update(id=100+index,size_in_bytes=archive.stat().st_size,digest='sha256:'+cli.sha(archive))
                    (base/'api.json').write_text(json.dumps(api))
                output=root/'out/native-original-matrix-results/native-original-matrix.json'
                reader=SimpleNamespace(native=SimpleNamespace(settings=lambda protocol:config),protocols=SimpleNamespace(V2='fixture-only'))
                with patch.object(cli,'ROOT',root),patch.object(cli,'context',return_value=head),patch.dict(os.environ,{'GITHUB_RUN_ID':'44'}),\
                     patch.object(cli.matrix.physical.persistence,'bind_owner',return_value=reader),patch.object(cli,'phase_proofs',return_value=([],aggregate,{})),\
                     patch.object(cli.matrix.physical,'guarded_sources',return_value={}):
                    if damage:
                        with self.assertRaisesRegex(ValueError,'full-frame'):cli.final_matrix(output)
                    else:
                        result=cli.final_matrix(output);self.assertEqual(len(result['direct_build_phases']),4)
                        self.assertEqual(result['actual_native_build_pairs'],304);self.assertFalse(result['qualification_granted'])
                actual=json.loads(output.read_text());self.assertEqual(actual['status'],'failed' if damage else 'passed-complete-native-original-physical-matrix-and-direct-build-gates-only')
                self.assertFalse(actual['phase6_complete']);self.assertTrue(actual['current_native_comparisons_pending'])


if __name__=='__main__':unittest.main()
