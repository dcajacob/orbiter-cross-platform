"""Small retained-byte and source-conservation controls; no runtime acceptance credit."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from contracts import ROOT,case_ids
import inspect_native_writer_receipts as receipts
import capture_hosted_native_reload as original
import capture_hosted_native_retry_reload as current
import hosted_native_retry_reload_reference as reference


class NativeAuditRetryTests(unittest.TestCase):
    def api(self,profile='Debug-automatic'):
        run_id,job_id,artifact_id,size,digest=receipts.PINS[profile];stage='Run all unchanged normal-host writer cases and independently inspect every result in matching userspace'
        job=dict(id=job_id,name='Normal native runtime stock writer '+profile.replace('-',' '),run_id=run_id,head_sha=receipts.SOURCE,
            status='completed',conclusion='success',labels=['ubuntu-24.04'],steps=[dict(name=stage,status='completed',conclusion='success')])
        controls=dict(job,id=1,name='controls',steps=[])
        run=dict(id=run_id,repository=dict(full_name='dcajacob/orbiter-cross-platform'),head_sha=receipts.SOURCE,
            head_branch='qualification/native-runtime-writer-'+profile.lower()+'-v2',path='.github/workflows/phase6-native-runtime-network-writers.yml',
            run_attempt=1,status='completed',conclusion='success')
        artifact=dict(id=artifact_id,name='normal-native-runtime-stock-writer-'+profile,size_in_bytes=size,digest='sha256:'+digest,expired=False,
            workflow_run=dict(id=run_id,head_sha=receipts.SOURCE))
        return dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),run=run,jobs=[controls,job],artifact=artifact)

    def test_only_all_complete_exact_profile_jobs_and_immutable_raw_artifacts_are_accepted(self):
        for profile in receipts.PINS:
            api=self.api(profile);receipts.validate_api(api,profile)
            for change in (lambda a:a['run'].update(run_attempt=2),lambda a:a['run'].update(conclusion='failure'),
                           lambda a:a['jobs'][1].update(labels=['self-hosted']),lambda a:a['jobs'][1]['steps'][0].update(conclusion='skipped'),
                           lambda a:a['artifact'].update(digest='sha256:'+'a'*64),lambda a:a['artifact'].update(expired=True)):
                changed=copy.deepcopy(api);change(changed)
                with self.assertRaises(ValueError):receipts.validate_api(changed,profile)

    def fixture(self,root,damage=False):
        profile='Debug-automatic';source=b'unchanged immutable source fixture\n';source_sha=hashlib.sha256(source).hexdigest()
        files={};cases={};prefix='native-stock-writer/'+profile+'/'
        for identity in case_ids():
            rows=[]
            for repeat in (1,2):
                body=(identity+str(repeat)).encode();name=prefix+identity+'-'+str(repeat)+'/observer-state.csv'
                rows.append(dict(files_sha256={'observer-state.csv':hashlib.sha256(body).hexdigest()}));files[name]=body
            cases[identity]=dict(runs=rows)
        capture=dict(status='captured-awaiting-independent-persistence-audit',phase='stock-writer',host='native-linux',
            producer_commit=receipts.SOURCE,runtime_source_commit=receipts.RUNTIME,runtime_role='normal',observer_delay_ms=120,
            process_receipts='owned-pid-start-argv-exit-v1',runtime_identity=dict(configuration='Debug',math_profile='automatic'),
            cases_requested=list(case_ids()),cases=cases,repeats=2,frames=960,failures={},diagnostic_only=False,
            owning_sources_runtime_probe_windows_inputs_assets_and_data_unchanged=True,native_admission_qualified=False,phase6_complete=False,
            source_sha256_lf={name:source_sha for name in receipts.MINIMUM})
        body=json.dumps(capture).encode();files[prefix+'capture.json']=body;csha=hashlib.sha256(body).hexdigest()
        audit=dict(status='audited-native-phase-only',profile=profile,phase='stock-writer',source_producer=receipts.SOURCE,
            runtime_source=receipts.RUNTIME,runtime_role='normal',actual_processes=76,actual_presentations=76*960,observer_delay_ms=120,
            capture_sha256=csha,owning_bytes_unchanged=True,diagnostic_only=False,phase6_complete=False,native_admission_qualified=False)
        body=json.dumps(audit).encode();top='hosted-native-writer/'+profile+'/'
        files[top+'independent-native-writer-audit.json']=body
        collection=dict(protocol='phase6-hosted-native-stock-writer-runtime-v3',status='captured-and-independently-audited-native-writers-only',
            profile=profile,collector_source=receipts.SOURCE,compiled_runtime_source=receipts.RUNTIME,actual_processes=76,
            capture_sha256=csha,independent_audit_sha256=hashlib.sha256(body).hexdigest(),phase6_complete=False,native_admission_qualified=False)
        files[top+'collection.json']=json.dumps(collection).encode()
        if damage:files[prefix+list(case_ids())[-1]+'-2/observer-state.csv']+=b'changed raw process bytes'
        archive=root/'writer.zip'
        with zipfile.ZipFile(archive,'w') as target:
            for name,body in files.items():target.writestr(name,body)
        pin=(*receipts.PINS[profile][:3],archive.stat().st_size,receipts.sha(archive))
        return profile,archive,pin,source

    def test_actual_source_and_every_recorded_process_member_are_verified_even_after_coherent_zip_rehash(self):
        for damage in (False,True):
            with tempfile.TemporaryDirectory() as temporary:
                profile,archive,pin,source=self.fixture(Path(temporary),damage)
                with patch.dict(receipts.PINS,{profile:pin}),patch.object(receipts.subprocess,'check_output',return_value=source):
                    api=self.api(profile)
                    if damage:
                        with self.assertRaises(ValueError):receipts.inspect(api,archive,profile)
                    else:
                        result=receipts.inspect(api,archive,profile)
                        self.assertEqual(result['actual_native_processes'],76);self.assertEqual(len(result['checked_retained_members_sha256']),79)
                        self.assertFalse(result['phase6_complete']);self.assertFalse(result['native_admission_qualified'])
                        self.assertTrue(result['full_physical_camera_frame_clock_saved_state_and_cross_comparisons_pending'])

    def test_full_reload_simulation_runtime_sanitizer_and_exact_saved_input_bodies_are_conserved(self):
        body=current.prepared_body().replace('from hosted_native_retry_reload_reference import','from hosted_native_reload_reference import')
        body=body.replace("protocol='phase6-hosted-native-exact-save-reload-retry-v2'","protocol='phase6-hosted-native-exact-save-reload-v1'")
        self.assertEqual(body,original.prepared_body())
        self.assertEqual((ROOT/'Tests/Production/Closeout/prepare_hosted_native_retry_reload.sh').read_text().replace('capture_hosted_native_retry_reload.py','capture_hosted_native_reload.py'),(ROOT/'Tests/Production/Closeout/prepare_hosted_native_reload.sh').read_text())

    def test_every_saved_input_and_extra_source_guard_must_stay_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'retained-input';path.write_bytes(b'original source')
            record=dict(protocol='phase6-hosted-audited-native-reload-retry-reference-v2',collector_source='e'*40,
                status='bound-exact-audited-original-parent-saves-only',saved_inputs=[dict(case=name,repeat=repeat) for name in case_ids() for repeat in (1,2)],
                original_saves_relabelled=False,native_admission_qualified=False,phase6_complete=False,guarded_files_sha256={str(path):reference.sha(path)})
            with patch.dict(os.environ,GITHUB_SHA='e'*40):
                self.assertEqual(reference.verify(record),record)
                path.write_bytes(b'changed source')
                with self.assertRaises(ValueError):reference.verify(record)
                changed=copy.deepcopy(record);changed['saved_inputs'].pop()
                with self.assertRaises(ValueError):reference.verify(changed)


if __name__=='__main__':unittest.main()
