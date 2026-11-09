"""Disposable acceptance/provenance fixtures; no runtime or qualification credit."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import current_native_matrix as matrix
import current_native_matrix_cli as cli


class CurrentNativeMatrixTests(unittest.TestCase):
    def config(self):
        return dict(cases=[dict(id='fixture%02d'%i) for i in range(38)],frames=960,budgets=dict(position_m=1e-5,rotation_rad=1e-10),image_ssim_minimum=.98)

    def pair(self):
        return dict(state={},camera={},ssim=1.,detail_calibration_only={},complete_saved_content_identical=True,actual_clocks_identical_lf=True)

    def report(self,cell=('Debug','automatic','stock')):
        ids=[c['id'] for c in self.config()['cases']]
        return dict(protocol='phase6-independent-shader-current-original-physical-phase-v2',status='passed-current-original-physical-phase-only',
            configuration=cell[0],math_profile=cell[1],phase=cell[2],auditor_source=matrix.SOURCE,
            compiled_application_source=matrix.capture.APPLICATION,compiled_observer_source=matrix.capture.APPLICATION,collector_source=matrix.capture.CAPTURE,
            profiles_required=4,matrix_cells_required=8,actual_current_processes=76,actual_captured_current_processes=76,actual_original_comparisons=76,
            successful_current_presentations=76*960,unchanged_budgets=self.config()['budgets'],unchanged_image_ssim_minimum=.98,
            complete_eight_cell_matrix_pending=True,direct_current_build_pairs_pending=True,native_comparisons_pending=True,
            serialization_roundtrips_pending=True,hardware_and_hands_on_pending=True,phase6_complete=False,native_admission_qualified=False,
            actual_job_id=matrix.JOBS[cell],current_decoded_members_sha256={'fixture':'a'*64},guarded_current_input_files_sha256={'fixture':'a'*64},
            guarded_sources_sha256={'fixture':'a'*64},guarded_independent_receipts_sha256={'fixture':'a'*64},actual_scalar_binding={'fixture':True},
            independent_original_retry_proof={'fixture':True},original_retry_reference_comparison=dict(API_attempts_normalized=False,old_failed_attempt_relabelled=False),
            cases={i:dict(runs=[dict(actual_observation=dict(observation={},complete_saved_state={},actual_class_inputs={},actual_simulation_data={},system_modules={}),
                direct_original_current=self.pair()) for n in range(2)],repeat=dict(raw_trace_bytes_identical=True,complete_saved_content_identical=True,ssim=1.)) for i in ids})

    def api(self,cell=('Debug','automatic','stock')):
        jobs=[]
        for key,ident in matrix.JOBS.items():
            jobs.append(dict(id=ident,name='Independently audit current original '+' '.join(key),run_id=matrix.RUN,head_sha=matrix.SOURCE,
                run_attempt=1,status='completed',conclusion='success',labels=['ubuntu-24.04'],
                steps=[dict(name=n,status='completed',conclusion='success') for n in matrix.STEPS]))
        jobs.append(dict(id=matrix.READINESS,name='readiness',run_id=matrix.RUN,head_sha=matrix.SOURCE,run_attempt=1,status='completed',
            conclusion='success',labels=['ubuntu-24.04'],steps=[dict(name=n,status='completed',conclusion='success') for n in matrix.READY_STEPS]))
        return dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),jobs=jobs,
            run=dict(id=matrix.RUN,head_sha=matrix.SOURCE,run_attempt=1,head_branch='qualification/current-shader-physical-audit-v1',
                path='.github/workflows/phase6-current-shader-physical-audit.yml',repository=dict(full_name='dcajacob/orbiter-cross-platform',private=False),status='completed',conclusion='success'),
            artifact=dict(id=123,name='shader-current-original-physical-'+'-'.join(cell),size_in_bytes=10,digest='sha256:'+'a'*64,expired=False,
                workflow_run=dict(id=matrix.RUN,head_sha=matrix.SOURCE)))

    def proof(self,cell,ident):
        return dict(cell=list(cell),api_artifact_id=ident,api_archive_sha256='sha256:'+'a'*64,physical_source=matrix.SOURCE,
            physical_report_sha256='b'*64,decoded_members_sha256={'fixture':'c'*64},report=self.report(cell),qualification_granted=False)

    def test_exact_complete_actual_physical_jobs_steps_runners_source_and_artifact_required(self):
        record=self.api();before=copy.deepcopy(record);matrix.api_identity(record,('Debug','automatic','stock'));self.assertEqual(record,before)
        for change in (lambda r:r['jobs'].pop(),lambda r:r['jobs'].append(copy.deepcopy(r['jobs'][0])),
            lambda r:r['jobs'][0].update(status='in_progress',conclusion=None),lambda r:r['jobs'][0]['steps'][2].update(conclusion='skipped'),
            lambda r:r['jobs'][-1]['steps'].pop(0),lambda r:r['jobs'][0]['labels'].append('self-hosted'),
            lambda r:r['run'].update(run_attempt=2),lambda r:r['run'].update(head_sha='f'*40),lambda r:r['run'].update(conclusion='failure'),
            lambda r:r['artifact'].update(expired=True),lambda r:r['artifact']['workflow_run'].update(head_sha='f'*40),
            lambda r:r['artifact'].update(name='current-original-physical-readiness')):
            changed=copy.deepcopy(record);change(changed)
            with self.assertRaises(ValueError):matrix.api_identity(changed,('Debug','automatic','stock'))

    def test_all_physical_cases_repeats_counts_budgets_and_pending_acceptance_must_be_conserved(self):
        report=self.report();matrix.phase_scope(report,('Debug','automatic','stock'),self.config())
        for change in (lambda r:r.update(actual_current_processes=75),lambda r:r['cases'].pop('fixture00'),
            lambda r:r['cases']['fixture00']['runs'].pop(),lambda r:r['unchanged_budgets'].update(rotation_rad=1e-9),
            lambda r:r.update(phase6_complete=True),lambda r:r.update(native_comparisons_pending=False),
            lambda r:r['original_retry_reference_comparison'].update(API_attempts_normalized=True),
            lambda r:r['cases']['fixture00']['runs'][0]['direct_original_current'].update(ssim=float('nan')),
            lambda r:r['cases']['fixture00']['runs'][0]['direct_original_current'].update(actual_clocks_identical_lf=False),
            lambda r:r['cases']['fixture00']['repeat'].update(complete_saved_content_identical=False)):
            changed=copy.deepcopy(report);change(changed)
            with self.assertRaises(ValueError):matrix.phase_scope(changed,('Debug','automatic','stock'),self.config())

    def test_all_eight_unique_phase_artifacts_are_required_without_qualification(self):
        proofs=[self.proof(c,i+1) for i,c in enumerate(matrix.JOBS)];result=matrix.aggregate(proofs,self.config())
        self.assertEqual(result['actual_direct_original_current_pairs'],608);self.assertFalse(result['phase6_complete']);self.assertFalse(result['qualification_granted'])
        for altered in (proofs[:-1],proofs+[proofs[0]],proofs[:-1]+[proofs[0]]):
            with self.assertRaises(ValueError):matrix.aggregate(altered,self.config())
        bad=copy.deepcopy(proofs);bad[1]['api_artifact_id']=bad[0]['api_artifact_id']
        with self.assertRaises(ValueError):matrix.aggregate(bad,self.config())

    def test_actual_phase_archive_bytes_are_verified_before_any_decode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);archive=root/'fixture.zip'
            with zipfile.ZipFile(archive,'w') as zipped:zipped.writestr('fixture','disposable fixture')
            api=self.api();api['artifact'].update(size_in_bytes=archive.stat().st_size,digest='sha256:'+matrix.sha(archive))
            archive.write_bytes(archive.read_bytes()+b'changed')
            with patch.object(matrix.native,'unpack') as decode:
                with self.assertRaises(ValueError):matrix.inspect_phase(api,archive,root/'decoded',('Debug','automatic','stock'),self.config())
                decode.assert_not_called()

    def test_report_owning_sources_are_re_read_from_exact_commit_and_not_rewritten(self):
        raw=b'fixture source';report=dict(guarded_sources_sha256={'Tests/Production/fixture.py':matrix.hashlib.sha256(raw).hexdigest()})
        before=copy.deepcopy(report)
        with patch.object(matrix.subprocess,'check_output',return_value=raw) as show:matrix.source_proof(report,matrix.SOURCE)
        self.assertEqual(report,before);self.assertIn(matrix.SOURCE+':Tests/Production/fixture.py',show.call_args.args[0])
        with patch.object(matrix.subprocess,'check_output',return_value=b'changed'):
            with self.assertRaises(ValueError):matrix.source_proof(report,matrix.SOURCE)

    def test_actual_staged_reload_bytes_and_complete_provenance_are_equal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);left=root/'current';right=root/'native';left.mkdir();right.mkdir()
            for folder in (left,right):(folder/'input.scn').write_bytes(b'original saved bytes')
            digest=matrix.sha(left/'input.scn');record=dict(persistence_input=dict(saved_input_sha256=digest),executed_case=dict(scenario_entry_point='input.scn'))
            supplied=dict(sha256=digest,parent_producer_commit=matrix.native.physical.original.SOURCE,parent_run='fixture-1',parent_capture_sha256='a'*64)
            result=cli.reload_input(left,right,record,copy.deepcopy(record),supplied);self.assertTrue(result['actual_staged_inputs_identical'])
            (right/'input.scn').write_bytes(b'changed')
            with self.assertRaises(ValueError):cli.reload_input(left,right,record,copy.deepcopy(record),supplied)

    def pair_report(self,phase='stock'):
        return dict(protocol='phase6-direct-current-native-and-current-build-phase-v1',status='passed-one-complete-direct-current-native-and-current-build-phase-only',
            auditor_source='a'*40,math_profile='automatic',phase=phase,required_cases=38,required_repeats=2,required_frames=960,
            actual_current_native_pairs=152,actual_current_build_pairs=76,complete_phase_aggregation={'fixture':'already independently verified'},
            unchanged_budgets=self.config()['budgets'],unchanged_image_ssim_minimum=.98,qualification_granted=False,phase6_complete=False,
            native_admission_qualified=False,other_class_lifetime_full157_and_hardware_gates_pending=True,full_four_pair_aggregation_pending=True,
            guarded_sources_sha256={'fixture':'a'*64},guarded_phase_and_reference_inputs_sha256={'fixture':'a'*64},actual_scalar_binding={'fixture':True},
            original_reference={'fixture':True},raw_observation_bindings={p:{} for p in ('Debug-automatic','Release-automatic')},
            original_retry_reference_comparisons={p:{c:dict(API_attempts_normalized=False,old_failed_attempt_relabelled=False) for c in ('current','native')} for p in ('Debug-automatic','Release-automatic')},
            cases={c['id']:dict(runs=[dict(current_build=self.pair(),current_native={cfg:dict(comparison=self.pair(),
                exact_saved_input=None if phase=='stock' else dict(actual_staged_inputs_identical=True,original_save_sha256='b'*64,
                    original_parent_capture_sha256='c'*64,original_parent_run=c['id']+'-'+str(n))) for cfg in ('Debug','Release')}) for n in (1,2)]) for c in self.config()['cases']})

    def test_final_scope_requires_actual_direct_pairs_full_cases_and_unchanged_budgets(self):
        report=self.pair_report();aggregate=report['complete_phase_aggregation'];cli.pair_scope(report,'automatic','stock','a'*40,aggregate,self.config())
        for change in (lambda r:r.update(actual_current_native_pairs=76),lambda r:r.update(actual_current_build_pairs=75),
            lambda r:r['cases'].pop('fixture00'),lambda r:r['cases']['fixture00']['runs'].pop(),
            lambda r:r['cases']['fixture00']['runs'][0]['current_native'].pop('Release'),
            lambda r:r['cases']['fixture00']['runs'][0]['current_native']['Debug']['comparison'].update(ssim=float('inf')),
            lambda r:r['cases']['fixture00']['runs'][0]['current_build'].update(complete_saved_content_identical=False),
            lambda r:r.update(other_class_lifetime_full157_and_hardware_gates_pending=False),lambda r:r.update(phase6_complete=True),
            lambda r:r.update(guarded_sources_sha256={}),lambda r:r['original_retry_reference_comparisons']['Debug-automatic']['native'].update(API_attempts_normalized=True)):
            altered=copy.deepcopy(report);change(altered)
            with self.assertRaises(ValueError):cli.pair_scope(altered,'automatic','stock','a'*40,aggregate,self.config())

    def test_final_reload_scope_requires_both_actual_original_saved_inputs(self):
        report=self.pair_report('reload');aggregate=report['complete_phase_aggregation'];cli.pair_scope(report,'automatic','reload','a'*40,aggregate,self.config())
        for changed_input in (None,dict(actual_staged_inputs_identical=False,original_save_sha256='b'*64,original_parent_capture_sha256='c'*64,original_parent_run='fixture-1')):
            bad=copy.deepcopy(report);bad['cases']['fixture00']['runs'][0]['current_native']['Release']['exact_saved_input']=changed_input
            with self.assertRaises((ValueError,TypeError)):cli.pair_scope(bad,'automatic','reload','a'*40,aggregate,self.config())

    def test_original_direct_comparison_wiring_resolves_to_conserved_owning_functions(self):
        import inspect,ast,subprocess
        function=matrix.native.physical.persistence.compare_pair
        self.assertTrue(callable(function));self.assertTrue(callable(matrix.observations.compare_windows_pair))
        for function,name,path in ((function,'compare_pair','Tests/Production/RemainingStockPersistence/audit.py'),
            (matrix.observations.compare_windows_pair,'compare_windows_pair','Tests/Production/CurrentWindows/Hosted/physical_observations.py')):
            source=subprocess.check_output(['git','-C',str(matrix.ROOT),'show',matrix.SOURCE+':'+path],text=True)
            old=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name)
            actual=ast.parse(inspect.getsource(function)).body[0]
            self.assertEqual(ast.dump(actual,include_attributes=False),ast.dump(old,include_attributes=False))
        self.assertEqual(cli.PAIRS,{(m,p) for m in ('automatic','sse2') for p in ('stock','reload')})

    def test_direct_loop_invokes_all_owned_comparisons_and_preserves_partial_failure(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);config=self.config();head='a'*40
            original={k:('a'*64 if 'sha256' in k else 1) for k in ('archive_sha256','archive_bytes','decoded_members_sha256','original_stock_job_id','transport_protocol')}
            restored=dict(original_api_archive_bindings={p:copy.deepcopy(original) for p in matrix.native.PROFILES})
            cps=[];nps=[];workers={};native_roots={}
            for cell in matrix.JOBS:
                report=dict(original_binding=copy.deepcopy(original),cases={c['id']:dict(runs=[dict(actual_observation=dict(observation=dict(actual_math='fma3'))) for n in (1,2)]) for c in config['cases']})
                cps.append(dict(cell=list(cell),report=report))
                profile=cell[0]+'-'+cell[1];phase=matrix.PHASES[cell[2]]
                nr=dict(independent_native_observations=dict(cases={c['id']:dict(runs=[dict(actual_math='fma3') for n in (1,2)]) for c in config['cases']}),
                    original_api_bindings={profile:copy.deepcopy(original)})
                nps.append(dict(profile=profile,phase=phase,report=nr))
            for cfg in ('Debug','Release'):
                profile=cfg+'-automatic';folder=root/profile;folder.mkdir();native_roots[profile]=folder
                records={c['id']:dict(runs=[dict(actual_math='fma3',persistence_input=None,executed_case=c) for n in (1,2)]) for c in config['cases']}
                (folder/'capture.json').write_text(json.dumps(dict(cases=records)))
                workers[profile]=dict(cases={'automatic-stock-'+k:v for k,v in records.items()})
            reader=SimpleNamespace(native=SimpleNamespace(settings=lambda p:config,shared=SimpleNamespace()),
                protocols=SimpleNamespace(V2={}),windows=SimpleNamespace(image_ssim=lambda *a:1.))
            def current(cell,*a,**kw):
                profile=cell[0]+'-'+cell[1]
                return root/('current-'+profile),dict(payload=str(root/('payload-'+profile))),{},workers[profile]
            def native(profile,*a,**kw):return native_roots[profile],dict(payload=str(root/('native-payload-'+profile)))
            def restoration(path):return restored
            with patch.object(cli,'ROOT',root),patch.object(cli,'context',return_value=head),patch.object(cli,'phase_proofs',return_value=(cps,nps,{'fixture':'aggregate'},{})),                 patch.object(matrix.native.physical.persistence,'bind_owner',return_value=reader),patch.object(cli.previous,'independent_reference',return_value=({}, {},restored)),                 patch.object(cli.previous,'scalar_binding',return_value={}),patch.object(matrix.native.physical,'guarded_sources',return_value={}),                 patch.object(matrix,'bind_raw',side_effect=current),patch.object(cli.previous,'bind_raw',side_effect=native),                 patch.object(cli.previous,'compare_reference',return_value={}),patch.object(cli,'load',side_effect=lambda p:restored if str(p).endswith('restoration.json') else json.loads(Path(p).read_text())),                 patch.object(matrix.native.physical.persistence,'compare_pair',return_value=self.pair()) as cross,                 patch.object(matrix.observations,'compare_windows_pair',return_value=self.pair()) as builds:
                output=root/'out/current-native-matrix-results/full.json';result=cli.direct_pairs('automatic','stock',output)
                self.assertEqual(cross.call_count,152);self.assertEqual(builds.call_count,76);self.assertEqual(result['actual_current_native_pairs'],152)
                self.assertFalse(result['phase6_complete']);self.assertEqual(len(result['cases']),38)
                cross.reset_mock();builds.reset_mock();cross.side_effect=[self.pair()]*5+[ValueError('deliberate physical fixture failure')]
                failed=root/'out/current-native-matrix-results/failed.json'
                with self.assertRaisesRegex(ValueError,'deliberate physical'):cli.direct_pairs('automatic','stock',failed)
                partial=json.loads(failed.read_text());self.assertEqual(partial['status'],'failed');self.assertEqual(partial['actual_current_native_pairs'],5)
                self.assertEqual(partial['actual_current_build_pairs'],2);self.assertFalse(partial['qualification_granted'])

    def pair_api(self,mode='automatic',phase='stock',head='a'*40,run_id=1234):
        jobs=[]
        for m,p in cli.PAIRS:jobs.append(dict(id=len(jobs)+1,name='Direct current native builds '+m+' '+p,run_id=run_id,head_sha=head,run_attempt=1,
            status='completed',conclusion='success',labels=['ubuntu-24.04'],steps=[dict(name=n,status='completed',conclusion='success') for n in cli.PAIR_STEPS]))
        jobs.append(dict(id=5,name='readiness',run_id=run_id,head_sha=head,run_attempt=1,status='completed',conclusion='success',labels=['ubuntu-24.04'],
            steps=[dict(name='Require all actual current and native physical phases',status='completed',conclusion='success')]))
        jobs.append(dict(id=6,name='Independently close all current native phases and direct comparisons',run_id=run_id,head_sha=head,run_attempt=1,status='in_progress',conclusion=None,labels=['ubuntu-24.04'],steps=[]))
        return dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),jobs=jobs,
            run=dict(id=run_id,head_sha=head,run_attempt=1,head_branch=cli.BRANCH,path=cli.WORKFLOW,status='in_progress',conclusion=None,
                repository=dict(full_name='dcajacob/orbiter-cross-platform',private=False)),
            artifact=dict(id=100,name='current-native-direct-build-'+mode+'-'+phase,expired=False,size_in_bytes=10,digest='sha256:'+'a'*64,
                workflow_run=dict(id=run_id,head_sha=head)))

    def test_same_source_all_pair_jobs_required_without_normalizing_active_final_run(self):
        record=self.pair_api();before=copy.deepcopy(record);cli.pair_api(record,'a'*40,1234,'automatic','stock');self.assertEqual(record,before)
        for change in (lambda r:r['jobs'].pop(0),lambda r:r['jobs'].append(copy.deepcopy(r['jobs'][0])),
            lambda r:r['jobs'][0].update(conclusion='failure'),lambda r:r['jobs'][0]['steps'][0].update(conclusion='skipped'),
            lambda r:r['jobs'][0]['labels'].append('self-hosted'),lambda r:r['run'].update(run_attempt=2),
            lambda r:r['run'].update(head_sha='b'*40),lambda r:r['artifact'].update(expired=True)):
            bad=copy.deepcopy(record);change(bad)
            with self.assertRaises(ValueError):cli.pair_api(bad,'a'*40,1234,'automatic','stock')

    def test_final_redecodes_all_four_actual_ZIPs_and_retains_partial_failure_on_tampering(self):
        import os
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);aggregate={'fixture':'already independently verified'};config=self.config()
            reader=SimpleNamespace(native=SimpleNamespace(settings=lambda p:config),protocols=SimpleNamespace(V2={}))
            for number,(mode,phase) in enumerate(sorted(cli.PAIRS),1):
                base=root/'out/current-matrix-pair-inputs'/(mode+'-'+phase);base.mkdir(parents=True)
                report=self.pair_report(phase);report['math_profile']=mode
                report['raw_observation_bindings']={p:{} for p in ('Debug-'+mode,'Release-'+mode)}
                report['original_retry_reference_comparisons']={p:{c:dict(API_attempts_normalized=False,old_failed_attempt_relabelled=False) for c in ('current','native')} for p in ('Debug-'+mode,'Release-'+mode)}
                with zipfile.ZipFile(base/'producer.zip','w') as zipped:zipped.writestr('current-native-matrix-results/'+mode+'-'+phase+'.json',json.dumps(report))
                api=self.pair_api(mode,phase);api['artifact'].update(id=number,size_in_bytes=(base/'producer.zip').stat().st_size,digest='sha256:'+matrix.sha(base/'producer.zip'))
                (base/'api.json').write_text(json.dumps(api))
            with patch.object(cli,'ROOT',root),patch.object(cli,'context',return_value='a'*40),patch.object(cli,'phase_proofs',return_value=([],[],aggregate,{})),                 patch.object(matrix.native.physical.persistence,'bind_owner',return_value=reader),patch.object(matrix.native.physical,'guarded_sources',return_value={}),                 patch.object(matrix,'source_proof') as sources,patch.object(matrix.native.shutil,'disk_usage',return_value=SimpleNamespace(free=32*1024**3)),                 patch.dict(os.environ,{'GITHUB_RUN_ID':'1234'}):
                output=root/'out/current-native-matrix-results/final.json';result=cli.final_matrix(output)
                self.assertEqual(len(result['direct_comparison_phases']),4);self.assertEqual(sources.call_count,4)
                self.assertEqual(result['actual_current_native_pairs'],608);self.assertEqual(result['actual_current_build_pairs'],304)
                self.assertFalse(result['qualification_granted']);self.assertFalse(result['phase6_complete'])
                damaged=root/'out/current-matrix-pair-inputs/sse2-stock/producer.zip';damaged.write_bytes(damaged.read_bytes()+b'tampered')
                # Retain the first successful decode tree exactly; use a fresh root for the failed proof inspection.
                import shutil
                shutil.rmtree(root/'out/current-matrix-pair-payload')
                failed=root/'out/current-native-matrix-results/failed-final.json'
                with self.assertRaises(ValueError):cli.final_matrix(failed)
                partial=json.loads(failed.read_text());self.assertEqual(partial['status'],'failed')
                self.assertEqual(len(partial['direct_comparison_phases']),3);self.assertFalse(partial['phase6_complete'])

    def test_raw_current_decode_creates_fresh_parent_and_keeps_actual_archive_member_guards(self):
        import hashlib
        from types import SimpleNamespace
        cell=('Debug','automatic','stock');label='-'.join(cell)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);base=root/'out/current-matrix-current-inputs'/label;base.mkdir(parents=True)
            request=dict(configuration='Debug',math_profile='automatic',phase='stock',source_commit=matrix.capture.APPLICATION)
            worker=dict(actual_processes=76,successful_presents=76*960,cases={'automatic-stock-'+c['id']:dict(runs=[{},{}]) for c in self.config()['cases']})
            files={'current-stock-requests/'+label+'/request.json':json.dumps(request).encode(),
                'current-stock-requests/'+label+'/worker-result.json':json.dumps(worker).encode(),
                'current-stock-exports/'+label+'/automatic-stock/fixture00-1/scene.rgba':b'disposable fixture frame'}
            with zipfile.ZipFile(base/'producer.zip','w') as zipped:
                for name,data in files.items():zipped.writestr(name,data)
            jobs=[dict(id=i+1,name='Source-complete current stock '+' '.join(c),run_id=matrix.capture.RUN,head_sha=matrix.capture.CAPTURE,
                status='completed',conclusion='success',labels=['windows-2025'],steps=[dict(name=n,status='completed',conclusion='success') for n in matrix.capture.REQUIRED_STEPS]) for i,c in enumerate(matrix.capture.EXPECTED)]
            jobs.append(dict(id=99,name='readiness',run_id=matrix.capture.RUN,head_sha=matrix.capture.CAPTURE,status='completed',conclusion='success',
                labels=['ubuntu-24.04'],steps=[dict(name='Require the complete successful immutable independent original audit',status='completed',conclusion='success')]))
            digest='sha256:'+matrix.sha(base/'producer.zip');size=(base/'producer.zip').stat().st_size
            api=dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),jobs=jobs,
                run=dict(id=matrix.capture.RUN,head_sha=matrix.capture.CAPTURE,run_attempt=1,head_branch='qualification/current-stock-capture-v4',
                    path='.github/workflows/phase6-current-shader-stock.yml',status='completed',conclusion='success',repository=dict(full_name='dcajacob/orbiter-cross-platform')),
                artifact=dict(id=123,name='shader-source-complete-current-stock-'+label,expired=False,digest=digest,size_in_bytes=size,
                    workflow_run=dict(id=matrix.capture.RUN,head_sha=matrix.capture.CAPTURE)))
            (base/'api.json').write_text(json.dumps(api))
            proof=dict(report=dict(current_decoded_members_sha256={n:hashlib.sha256(b).hexdigest() for n,b in files.items()},
                current_api_archive_sha256=digest,current_api_archive_bytes=size,cases={c['id']:{} for c in self.config()['cases']}))
            parent=root/'out/current-matrix-current-payload';self.assertFalse(parent.exists())
            with patch.object(matrix,'ROOT',root),patch.object(matrix.native.shutil,'disk_usage',return_value=SimpleNamespace(free=32*1024**3)):
                folder,binding,actual_request,actual_worker=matrix.bind_raw(cell,proof)
                self.assertTrue(parent.is_dir());self.assertEqual(actual_request,request);self.assertEqual(actual_worker,worker)
                (folder/'fixture00-1/scene.rgba').write_bytes(b'changed')
                with self.assertRaises(ValueError):matrix.bind_raw(cell,proof,Path(binding['payload']),decode=False)

    def test_workflow_never_runs_simulators_or_builds_and_preserves_all_partial_outputs(self):
        text=(matrix.ROOT/'.github/workflows/phase6-current-native-matrix.yml').read_text()
        self.assertEqual(text.count('runs-on: ubuntu-24.04'),3);self.assertIn('max-parallel: 2',text);self.assertIn('cancel-in-progress: false',text)
        self.assertEqual(text.count('if: always()'),3)
        for token in ('cmake --build','orbiter-production --','windows-2025','larger-runner'):self.assertNotIn(token,text)
        self.assertIn('current_native_matrix_cli.py --final',text)
