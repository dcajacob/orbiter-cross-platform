"""Disposable reload ZIP/reference fixtures only; no native physical acceptance credit."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from contracts import ROOT,case_ids
import inspect_native_reload_receipts as receipts

HOSTED=ROOT/'Tests/Production/CurrentWindows/Hosted';sys.path.insert(0,str(HOSTED))
import source_complete_retry_provider as provider


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


old=module('native_reload_raw_writer_fixture',ROOT/'Tests/Production/Closeout/NativeAuditRetry.Test.py')
retry=module('native_reload_raw_retry_fixture',ROOT/'Tests/Production/Closeout/CurrentAuditRetry.Test.py')


class NativeReloadReceiptTests(unittest.TestCase):
    def api(self,profile):
        run_id,job_id,artifact_id,size,digest=receipts.PINS[profile]
        job=dict(id=job_id,name='Native exact original save reload '+profile.replace('-',' '),run_id=run_id,head_sha=receipts.SOURCE,
            status='completed',conclusion='success',labels=['ubuntu-24.04'],steps=[dict(name=
            'Run all unchanged normal-host exact-save reloads and independently inspect every result in matching userspace',status='completed',conclusion='success')])
        controls=dict(job,id=1,name='controls',steps=[])
        run=dict(id=run_id,repository=dict(full_name='dcajacob/orbiter-cross-platform'),head_sha=receipts.SOURCE,
            head_branch='qualification/native-stock-reload-'+profile.lower()+'-v3',path='.github/workflows/phase6-native-retry-stock-reloads.yml',
            run_attempt=1,status='completed',conclusion='success')
        artifact=dict(id=artifact_id,name='retry-native-stock-reload-'+profile,size_in_bytes=size,digest='sha256:'+digest,expired=False,
            workflow_run=dict(id=run_id,head_sha=receipts.SOURCE))
        return dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),run=run,jobs=[controls,job],artifact=artifact)

    def test_exact_completed_reload_source_job_and_new_api_artifact_are_required(self):
        for profile in receipts.PINS:
            api=self.api(profile);receipts.validate_api(api,profile)
            for change in (lambda a:a['run'].update(run_attempt=2),lambda a:a['run'].update(head_sha=old.receipts.SOURCE),
                           lambda a:a['run'].update(status='in_progress',conclusion=None),lambda a:a['jobs'][1]['steps'][0].update(conclusion='skipped'),
                           lambda a:a['artifact'].update(id=old.receipts.PINS[profile][2]),lambda a:a['artifact'].update(expired=True),
                           lambda a:a['jobs'][1].update(labels=['ubuntu-24.04','self-hosted'])):
                changed=copy.deepcopy(api);change(changed)
                with self.assertRaises(ValueError):receipts.validate_api(changed,profile)

    def fixture(self,root,out,cfg,restored,mode=None):
        profile,old_archive,_,source=old.NativeAuditRetryTests().fixture(root)
        with zipfile.ZipFile(old_archive) as archive:
            files={name.replace('native-stock-writer/','native-stock-reload/').replace('hosted-native-writer/','hosted-native-reload/'):
                archive.read(name) for name in archive.namelist()}
        prefix='native-stock-reload/'+profile+'/';top='hosted-native-reload/'+profile+'/'
        capture=json.loads(files[prefix+'capture.json']);capture.update(phase='windows-save-reload',producer_commit=receipts.SOURCE,windows_parent_producer=receipts.ORIGINAL)
        writer=json.loads(Path(cfg['reference_audit']['path']).read_text());parent_sha=writer['profiles'][profile]['capture_sha256']
        members={'remaining-stock-repaired/capture.json':parent_sha};saves=[];guards={}
        parent=Path('/home/runner/work/orbiter-cross-platform/orbiter-cross-platform/out/original-stock-audit/transport')/profile/'remaining-stock-repaired'
        cases={case['id']:case for case in json.loads((ROOT/'Tests/Production/RemainingStock/cases.json').read_text())['cases']}
        for identity in case_ids():
            for repeat,row in enumerate(capture['cases'][identity]['runs'],1):
                body=('fixture saved input '+identity+' '+str(repeat)).encode();checksum=hashlib.sha256(body).hexdigest()
                relative=identity+'-'+str(repeat)+'/Scenarios/(Current state).scn';members['remaining-stock-repaired/'+relative]=checksum
                saves.append(dict(case=identity,repeat=repeat,path=str(parent/relative),sha256=checksum));guards[str(parent/relative)]=checksum
                entry='Scenarios/_Phase6Persistence/'+identity+'/'+Path(cases[identity]['scenario']).name
                provenance=dict(parent_producer_commit=receipts.ORIGINAL,parent_capture_sha256=parent_sha,parent_run=identity+'-'+str(repeat),
                    saved_input_sha256=checksum,derived_scenario_entry_point=entry)
                base=prefix+identity+'-'+str(repeat)+'/'
                files[base+entry]=body;files[base+'persistence-input.json']=json.dumps(provenance).encode()
                row.update(persistence_input=provenance,executed_case=dict(scenario_entry_point=entry))
                row['files_sha256'].update({entry:checksum,'persistence-input.json':hashlib.sha256(files[base+'persistence-input.json']).hexdigest()})
        restored.update(restorer_source=receipts.SOURCE)
        restored['original_api_archive_bindings'][profile]=dict(decoded_members_sha256=members)
        Path(cfg['reference_restoration']['path']).write_text(json.dumps(restored));cfg['reference_restoration']['sha256']=receipts.sha(cfg['reference_restoration']['path'])
        cfg['roles']['runner']['commit']=receipts.SOURCE;proof=provider.reference_receipts(cfg)
        reference=dict(protocol='phase6-hosted-audited-native-reload-retry-reference-v2',status='bound-exact-audited-original-parent-saves-only',
            collector_source=receipts.SOURCE,profile=profile,original=proof,original_saves_relabelled=False,phase6_complete=False,native_admission_qualified=False,
            capture=str(parent),parent_capture_sha256=parent_sha,saved_inputs=saves,guarded_files_sha256=guards)
        if mode=='coherent-saved-substitution':
            identity=list(case_ids())[0];row=capture['cases'][identity]['runs'][0];entry=row['executed_case']['scenario_entry_point'];base=prefix+identity+'-1/'
            files[base+entry]=b'changed saved input';checksum=hashlib.sha256(files[base+entry]).hexdigest()
            row['persistence_input']['saved_input_sha256']=checksum;row['files_sha256'][entry]=checksum
            files[base+'persistence-input.json']=json.dumps(row['persistence_input']).encode();row['files_sha256']['persistence-input.json']=hashlib.sha256(files[base+'persistence-input.json']).hexdigest()
            saves[0]['sha256']=checksum;guards[saves[0]['path']]=checksum
        capture_body=json.dumps(capture).encode();files[prefix+'capture.json']=capture_body;csha=hashlib.sha256(capture_body).hexdigest()
        audit_name=top+'independent-native-writer-audit.json';audit=json.loads(files.pop(audit_name))
        audit.update(phase='windows-save-reload',source_producer=receipts.SOURCE,capture_sha256=csha)
        body=json.dumps(audit).encode();files[top+'independent-native-reload-audit.json']=body
        collection=json.loads(files[top+'collection.json']);collection.update(protocol='phase6-hosted-native-exact-save-reload-retry-v2',
            status='captured-and-independently-audited-native-exact-save-reloads-only',collector_source=receipts.SOURCE,capture_sha256=csha,
            independent_audit_sha256=hashlib.sha256(body).hexdigest(),original_reference=reference)
        files[top+'collection.json']=json.dumps(collection).encode()
        for path in out.rglob('*'):
            if path.is_file():files[path.relative_to(out).as_posix()]=path.read_bytes()
        if mode=='raw-process':files[prefix+list(case_ids())[-1]+'-2/observer-state.csv']+=b'changed raw bytes'
        if mode=='first-failed-zip':files['reference-api/first.zip']+=b'changed exact failed attempt'
        archive=root/'reload-fixture.zip'
        with zipfile.ZipFile(archive,'w') as target:
            for name,body in files.items():target.writestr(name,body)
        pin=(42586897811,129058969708,80001,archive.stat().st_size,receipts.sha(archive))
        return profile,archive,pin,source

    def verify_fixture(self,mode=None):
        original=retry.old.reference_fixture.SourceCompleteReferenceTests.receipts
        def complete_parent_fields(instance):
            values=original(instance)
            for profile in values[1]['profiles'].values():profile['capture_sha256']='c'*64
            return values
        with patch.object(retry.old.reference_fixture.SourceCompleteReferenceTests,'receipts',complete_parent_fields):
            with tempfile.TemporaryDirectory() as temporary,retry.CurrentAuditRetryTests().evidence() as (out,cfg,restored,manifest):
                profile,archive,pin,source=self.fixture(Path(temporary),out,cfg,restored,mode)
                with patch.dict(receipts.PINS,{profile:pin}),patch.object(receipts.subprocess,'check_output',return_value=source):
                    return receipts.inspect(self.api(profile),archive,profile)

    def test_complete_raw_reload_members_and_all_76_original_saves_are_reverified_without_runtime_credit(self):
        result=self.verify_fixture();self.assertEqual(result['actual_native_processes'],76)
        self.assertEqual(result['original_reference']['exact_original_saved_inputs'],76)
        self.assertFalse(result['phase6_complete']);self.assertFalse(result['native_admission_qualified'])
        self.assertTrue(result['full_physical_camera_frame_clock_saved_state_and_cross_comparisons_pending'])

    def test_changed_raw_process_or_first_failure_zip_cannot_pass_after_coherent_outer_archive_rehash(self):
        for mode in ('raw-process','first-failed-zip'):
            with self.assertRaises(ValueError):self.verify_fixture(mode)

    def test_coherently_rehashed_scenario_and_descriptor_cannot_replace_the_audited_original_save(self):
        with self.assertRaises(ValueError):self.verify_fixture('coherent-saved-substitution')


if __name__=='__main__':unittest.main()
