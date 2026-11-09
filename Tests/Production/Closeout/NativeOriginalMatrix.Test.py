"""Disposable matrix/API/archive/budget controls; no simulator or runtime acceptance credit."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock,patch
import zipfile
import native_original_matrix as matrix


class NativeOriginalMatrixTests(unittest.TestCase):
    def config(self):
        return dict(cases=[dict(id='fixture%02d'%i) for i in range(38)],frames=960,
            budgets=dict(position_m=1e-5,rotation_rad=1e-10),image_ssim_minimum=.98)

    def report(self,profile='Debug-automatic',phase='stock-writer'):
        config=self.config();ids=[c['id'] for c in config['cases']]
        native=dict(status='audited-native-phase-only',profile=profile,phase=phase,
            source_producer=matrix.physical.writers.SOURCE if phase=='stock-writer' else matrix.physical.reloads.SOURCE,
            runtime_source=matrix.physical.writers.RUNTIME,runtime_role='normal',observer_delay_ms=120,
            actual_processes=76,actual_presentations=76*960,owning_bytes_unchanged=True,diagnostic_only=False,
            phase6_complete=False,native_admission_qualified=False,cases={i:dict(runs=[{},{}]) for i in ids})
        pair=dict(state={},camera={},detail_calibration_only={},ssim=1.0,complete_saved_content_identical=True,actual_clocks_identical_lf=True)
        report=dict(protocol='phase6-independent-native-original-complete-physical-phase-v1',
            status='passed-one-complete-native-original-physical-phase-only',profile=profile,phase=phase,auditor_source=matrix.SOURCE,
            native_source=native['source_producer'],compiled_runtime_source=matrix.physical.writers.RUNTIME,
            required_profiles=4,required_phases=2,required_cases=38,required_repeats=2,required_frames=960,
            actual_native_processes=76,actual_direct_original_native_pairs=76,successful_native_presentations=76*960,
            unchanged_budgets=config['budgets'],unchanged_image_ssim_minimum=.98,
            complete_four_profile_two_phase_matrix_pending=True,direct_native_and_original_build_pairs_pending=True,
            current_native_comparisons_pending=True,other_class_lifetime_full157_and_hardware_gates_pending=True,
            qualification_granted=False,phase6_complete=False,native_admission_qualified=False,
            independent_native_observations=native,independent_original_observations=dict(producer_commit=matrix.physical.original.SOURCE,
                stock=dict(cases={i:dict(runs=[{},{}]) for i in ids}),reload=dict(cases={i:dict(runs=[{},{}]) for i in ids},actual_processes=76)),
            cases={i:dict(runs=[dict(direct_original_native=copy.deepcopy(pair),original_windows_roundtrip=dict(actual_field_changes={})) for j in range(2)]) for i in ids},
            original_api_bindings={p:{} for p in matrix.PROFILES},guarded_sources_sha256={'fixture-source':'a'*64},
            guarded_runtime_and_preserved_original_inputs_sha256={'fixture-runtime':'b'*64},native_decoded_tree_sha256={'capture.json':'c'*64},
            raw_native_proof=dict(archive_sha256='d'*64),native_API_archive_sha256='sha256:'+'d'*64)
        return report

    def api(self,profile='Debug-automatic',phase='stock-writer'):
        jobs=[]
        for (p,q),ident in matrix.JOBS.items():
            jobs.append(dict(id=ident,name='Independently compare original native '+p+' '+q,run_id=matrix.RUN,head_sha=matrix.SOURCE,
                run_attempt=1,status='completed',conclusion='success',labels=['ubuntu-24.04'],steps=[dict(name=n,status='completed',conclusion='success') for n in matrix.STEPS]))
        jobs.append(dict(id=129187580614,name='readiness',run_id=matrix.RUN,head_sha=matrix.SOURCE,run_attempt=1,
            status='completed',conclusion='success',labels=['ubuntu-24.04'],steps=[dict(name=n,status='completed',conclusion='success') for n in (
                'Preserve every original and added small helper control','Require actual full original retry restoration and complete native retained-byte proofs','Run actions/upload-artifact@v7')]))
        return dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),jobs=jobs,
            run=dict(id=matrix.RUN,head_sha=matrix.SOURCE,run_attempt=1,head_branch='qualification/native-original-physical-audit-v1',
                path='.github/workflows/phase6-native-original-physical-audit.yml',repository=dict(full_name='dcajacob/orbiter-cross-platform',private=False),status='completed',conclusion='success'),
            artifact=dict(id=123,name='native-original-physical-'+profile+'-'+phase,size_in_bytes=10,digest='sha256:'+'a'*64,expired=False,
                workflow_run=dict(id=matrix.RUN,head_sha=matrix.SOURCE)))

    def proof(self,profile,phase,ident):
        return dict(protocol='phase6-verified-complete-native-original-physical-phase-artifact-v1',profile=profile,phase=phase,
            api_artifact_id=ident,api_archive_sha256='sha256:'+'a'*64,physical_source=matrix.SOURCE,
            physical_report_sha256='b'*64,decoded_members_sha256={'fixture':'c'*64},report=self.report(profile,phase),
            full_matrix_and_direct_build_gates_pending=True,qualification_granted=False)

    def test_all_eight_unique_full_phases_required_and_aggregation_preserves_remaining_gates(self):
        proofs=[self.proof(p,q,i+1) for i,(p,q) in enumerate(matrix.JOBS)]
        result=matrix.complete_phase_matrix(proofs,self.config());self.assertEqual(result['actual_direct_original_native_pairs'],608)
        self.assertFalse(result['qualification_granted']);self.assertFalse(result['phase6_complete']);self.assertTrue(result['direct_native_and_original_build_pairs_pending'])
        for mutated in (proofs[:-1],proofs+[proofs[0]],proofs[:-1]+[proofs[0]]):
            with self.assertRaises(ValueError):matrix.complete_phase_matrix(mutated,self.config())
        for change in (lambda p:p[0].update(physical_source='f'*40),lambda p:p[0].update(api_artifact_id=p[1]['api_artifact_id']),
                       lambda p:p[0].update(decoded_members_sha256={}),lambda p:p[0].update(qualification_granted=True)):
            altered=copy.deepcopy(proofs);change(altered)
            with self.assertRaises(ValueError):matrix.complete_phase_matrix(altered,self.config())

    def test_each_phase_requires_all_actual_processes_both_original_phases_and_unchanged_budgets(self):
        report=self.report();self.assertEqual(matrix.phase_scope(report,'Debug-automatic','stock-writer',self.config()),76)
        mutations=[lambda r:r.update(required_frames=959),lambda r:r.update(actual_direct_original_native_pairs=75),
            lambda r:r['independent_native_observations']['cases'].pop('fixture00'),lambda r:r['independent_original_observations']['reload']['cases']['fixture00']['runs'].pop(),
            lambda r:r['cases']['fixture00']['runs'][0]['direct_original_native'].update(complete_saved_content_identical=False),
            lambda r:r['cases']['fixture00']['runs'][0]['direct_original_native'].update(actual_clocks_identical_lf=False),
            lambda r:r['cases']['fixture00']['runs'][0]['direct_original_native'].update(ssim=float('nan')),
            lambda r:r['cases']['fixture00']['runs'][0]['direct_original_native'].update(ssim=.979),
            lambda r:r.update(unchanged_budgets={}),lambda r:r.update(phase6_complete=True),
            lambda r:r.update(direct_native_and_original_build_pairs_pending=False),lambda r:r['original_api_bindings'].pop('Release-sse2')]
        for mutate in mutations:
            altered=copy.deepcopy(report);mutate(altered)
            with self.assertRaises(ValueError):matrix.phase_scope(altered,'Debug-automatic','stock-writer',self.config())

    def test_pending_wrong_source_attempt_steps_or_runner_cannot_supply_closed_api_producer(self):
        matrix.api_identity(self.api(),'Debug-automatic','stock-writer')
        for mutate in (lambda r:r['run'].update(status='in_progress'),lambda r:r['run'].update(run_attempt=2),
                       lambda r:r['run'].update(head_sha='e'*40),lambda r:r['jobs'].pop(),
                       lambda r:r['jobs'][0].update(labels=['self-hosted']),lambda r:r['jobs'][0]['steps'][0].update(conclusion='skipped'),
                       lambda r:r['artifact'].update(expired=True),lambda r:r['artifact']['workflow_run'].update(head_sha='e'*40)):
            record=self.api();mutate(record)
            with self.assertRaises(ValueError):matrix.api_identity(record,'Debug-automatic','stock-writer')

    def test_report_archive_length_hash_bootstrap_and_every_decoded_member_are_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);archive=root/'proof.zip';profile='Debug-automatic';phase='stock-writer';cell=profile+'-'+phase
            report=json.dumps(self.report()).encode();bootstrap=dict(protocol='phase6-hosted-native-original-physical-bootstrap-v1',
                status='audited-one-complete-retained-native-original-physical-phase-only',profile=profile,collector_source=matrix.SOURCE,
                compiled_runtime_source=matrix.physical.writers.RUNTIME,simulator_executed=False,actual_native_processes=76,
                actual_direct_original_native_pairs=76,physical_report_sha256=hashlib.sha256(report).hexdigest(),phase6_complete=False,native_admission_qualified=False)
            with zipfile.ZipFile(archive,'w') as out:
                out.writestr('native-original-physical-audits/'+cell+'.json',report)
                out.writestr('native-original-bootstrap/'+cell+'/collection.json',json.dumps(bootstrap))
            api=self.api();api['artifact'].update(size_in_bytes=archive.stat().st_size,digest='sha256:'+matrix.sha(archive))
            checked=matrix.inspect_phase(api,archive,root/'decoded',profile,phase,self.config());self.assertEqual(len(checked['decoded_members_sha256']),2)
            altered=copy.deepcopy(api);altered['artifact']['digest']='sha256:'+'f'*64
            with self.assertRaises(ValueError):matrix.inspect_phase(altered,archive,root/'damaged',profile,phase,self.config())
            self.assertFalse((root/'damaged').exists())
            (root/'decoded/native-original-physical-audits'/(cell+'.json')).write_bytes(b'changed')
            with self.assertRaises(ValueError):matrix.physical.original.legacy.inspect_archive(archive,root/'decoded',api['artifact']['digest'][7:],api['artifact']['size_in_bytes'])

    def test_archive_capacity_reserve_and_unsafe_names_cannot_be_bypassed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);archive=root/'unsafe.zip'
            with zipfile.ZipFile(archive,'w') as out:out.writestr('../outside','fixture')
            api=self.api();api['artifact'].update(size_in_bytes=archive.stat().st_size,digest='sha256:'+matrix.sha(archive))
            with patch.object(matrix.shutil,'disk_usage',return_value=SimpleNamespace(free=8*1024**3)):
                with self.assertRaisesRegex(ValueError,'reserve'):matrix.inspect_phase(api,archive,root/'reserve','Debug-automatic','stock-writer',self.config())
            with self.assertRaises((ValueError,RuntimeError)):matrix.inspect_phase(api,archive,root/'unsafe','Debug-automatic','stock-writer',self.config())
            self.assertFalse((root/'outside').exists())

    def test_direct_build_comparison_executes_original_functions_with_full_frame_and_original_budget(self):
        with tempfile.TemporaryDirectory() as temporary:
            left=Path(temporary)/'left';right=Path(temporary)/'right';left.mkdir();right.mkdir()
            (left/'scene.rgba').write_bytes(b'fixture-left');(right/'scene.rgba').write_bytes(b'fixture-right')
            reader=SimpleNamespace(windows=SimpleNamespace(image_ssim=Mock(return_value=.99)),original_audit=SimpleNamespace(
                compare_state=Mock(return_value={'fixture':1}),camera_comparison=Mock(return_value={'fixture':2}),detail_calibration=Mock(return_value={'fixture':3})))
            config=self.config();result=matrix.compare_build_pair(left,right,reader,config)
            self.assertEqual(result['ssim'],.99);reader.windows.image_ssim.assert_called_once_with(b'fixture-left',b'fixture-right',1280,720)
            for name in ('compare_state','camera_comparison'):getattr(reader.original_audit,name).assert_called_once_with(left,right,config)
            for score in (.979,float('nan')):
                reader.windows.image_ssim.return_value=score
                with self.assertRaises(ValueError):matrix.compare_build_pair(left,right,reader,config)
            reader.windows.image_ssim.return_value=1;reader.original_audit.compare_state.side_effect=ValueError('original state budget exceeded')
            with self.assertRaisesRegex(ValueError,'original state budget'):matrix.compare_build_pair(left,right,reader,config)


if __name__=='__main__':unittest.main()
