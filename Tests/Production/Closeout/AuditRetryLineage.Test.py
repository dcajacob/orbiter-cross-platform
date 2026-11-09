"""Small exact-lineage and real ZIP fixtures only; no simulation acceptance credit."""
import ast
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
from contracts import ROOT

sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
import restore_source_complete_reference as prior
import restore_source_complete_retry_reference as restored
import audit_retry_lineage as retry

spec=importlib.util.spec_from_file_location('retry_original_API_fixture',ROOT/'Tests/Production/Closeout/SourceCompleteOriginal.Test.py')
original_fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(original_fixture)


class ExactOriginalAuditRetryTests(unittest.TestCase):
    def api(self,attempt=1):
        first=attempt==1
        start='2026-11-09T06:22:49Z' if first else '2026-11-09T06:34:38Z'
        end='2026-11-09T06:25:42Z' if first else '2026-11-09T07:12:52Z'
        upload='2026-11-09T06:25:41Z' if first else '2026-11-09T07:12:49Z'
        steps=[dict(name=name,status='completed',conclusion=('success' if n<3 or n==7 else 'failure' if n==3 else 'skipped') if first else 'success')
            for n,name in enumerate(prior.STEPS)]
        run=dict(id=retry.RUN,repository=dict(full_name='dcajacob/orbiter-cross-platform'),head_sha=retry.AUDITOR,
            head_branch=retry.BRANCH,path=retry.WORKFLOW,run_attempt=attempt,status='completed',conclusion='failure' if first else 'success')
        job=dict(id=retry.FIRST_JOB if first else retry.RETRY_JOB,name='audit',run_id=retry.RUN,head_sha=retry.AUDITOR,
            head_branch=retry.BRANCH,status='completed',conclusion=run['conclusion'],labels=['ubuntu-24.04'],steps=steps,started_at=start,completed_at=end)
        artifact=dict(id=retry.FIRST_ARTIFACT if first else retry.RETRY_ARTIFACT,name=retry.ARTIFACT_NAME,
            expired=False,size_in_bytes=retry.FIRST_SIZE if first else retry.RETRY_SIZE,digest='sha256:'+(retry.FIRST_DIGEST if first else retry.RETRY_DIGEST),
            workflow_run=dict(id=retry.RUN,head_sha=retry.AUDITOR,head_branch=retry.BRANCH),created_at=upload,updated_at=upload)
        return dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),run=run,jobs=[job],artifact=artifact)

    def test_only_the_specific_failed_first_attempt_and_exact_failure_stage_are_accepted(self):
        api=self.api();before=copy.deepcopy(api);retry.validate_first_api(api,prior.STEPS);self.assertEqual(before,api)
        changes=[lambda r:r['run'].update(run_attempt=2),lambda r:r['run'].update(head_sha='f'*40),
            lambda r:r['jobs'][0].update(id=retry.FIRST_JOB+1),lambda r:r['jobs'][0].update(labels=['self-hosted']),
            lambda r:r['jobs'][0]['steps'][3].update(conclusion='success'),lambda r:r['jobs'][0]['steps'][6].update(conclusion='success'),
            lambda r:r['artifact'].update(id=retry.FIRST_ARTIFACT+1),lambda r:r['artifact'].update(digest='sha256:'+'b'*64),
            lambda r:r['artifact'].update(expired=True)]
        for change in changes:
            modified=copy.deepcopy(api);change(modified)
            with self.assertRaises(ValueError):retry.validate_first_api(modified,prior.STEPS)

    def test_retry_requires_exact_source_job_attempt_all_checks_and_its_own_upload_interval(self):
        api=self.api(2);before=copy.deepcopy(api);restored.validate_audit_api(api);self.assertEqual(before,api)
        with self.assertRaises(ValueError):prior.validate_audit_api(api)
        changes=[lambda r:r['run'].update(run_attempt=1),lambda r:r['run'].update(run_attempt=3),
            lambda r:r['run'].update(conclusion='failure'),lambda r:r['jobs'][0].update(id=retry.FIRST_JOB),
            lambda r:r['jobs'][0]['steps'][6].update(conclusion='skipped'),lambda r:r['jobs'][0].update(labels=['self-hosted']),
            lambda r:r['artifact'].update(id=retry.FIRST_ARTIFACT),lambda r:r['artifact'].update(created_at='2026-11-09T06:25:41Z'),
            lambda r:r['artifact'].update(updated_at='2026-11-09T08:00:01Z'),lambda r:r['artifact'].update(size_in_bytes=0),lambda r:r['artifact'].update(id=retry.RETRY_ARTIFACT+1),
            lambda r:r['artifact'].update(size_in_bytes=retry.RETRY_SIZE+1),lambda r:r['artifact'].update(digest='sha256:'+'a'*64),
            lambda r:r['artifact']['workflow_run'].update(head_sha='c'*40)]
        for change in changes:
            modified=copy.deepcopy(api);change(modified)
            with self.assertRaises(ValueError):restored.validate_audit_api(modified)

    def evidence(self,root,change=None):
        run,jobs=original_fixture.SourceCompleteOriginalTests().record();normalized=prior.transport.run_identity(run,jobs)
        artifacts=[dict(id=9000+n,name='matched-clock-remaining-stock-v2-'+profile,size_in_bytes=123,
            digest='sha256:'+'c'*64,expired=False,workflow_run=dict(id=prior.transport.RUN,head_sha=prior.ORIGINAL,head_branch=prior.transport.BRANCH))
            for n,profile in enumerate(sorted(prior.PROFILES))]
        manifest=dict(status='passed',protocol=prior.transport.PROTOCOL,source_commit=prior.ORIGINAL,
            diagnostic_only=False,phase6_complete=False,native_admission_qualified=False,workflow_run=normalized,
            artifacts=[dict(profile=a['name'].removeprefix('matched-clock-remaining-stock-v2-'),api_artifact=a) for a in artifacts])
        recorded=dict(workflow_run=run,jobs=jobs,artifacts=artifacts)
        controls=dict(status='passed',producer_commit=retry.AUDITOR,sources_match_producer=True,tests_run=176,
            skipped=0,failures=0,errors=0,phase6_complete=False)
        files={'original-stock-audit/api-records.json':recorded,'original-stock-audit/transport/download.json':manifest,
               'original-stock-audit-controls.json':controls}
        if change:change(files)
        archive=root/'first.zip'
        with zipfile.ZipFile(archive,'w') as source:
            for name,value in files.items():source.writestr(name,json.dumps(value))
        log=root/'first.log';log.write_bytes(b'Tests/Production/Cockpit/frozen.py\nurllib.error.HTTPError: HTTP Error 504: Gateway Time-out\n')
        pins=dict(FIRST_SIZE=archive.stat().st_size,FIRST_DIGEST=retry.sha(archive),FIRST_LOG_SIZE=log.stat().st_size,FIRST_LOG_DIGEST=retry.sha(log))
        return archive,log,pins

    def test_actual_failed_zip_log_and_all_partial_outputs_are_preserved_without_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);archive,log,pins=self.evidence(root)
            with patch.multiple(retry,**pins):
                api=self.api();before=copy.deepcopy(api)
                actual=retry.inspect_first_evidence(api,archive,log,root/'decoded',prior)
                self.assertEqual(before,api);self.assertEqual(actual['first_attempt'],1)
                self.assertFalse(actual['API_attempts_normalized']);self.assertFalse(actual['old_failed_attempt_relabelled'])
                self.assertFalse(actual['qualification_granted']);self.assertEqual(set(actual['first_decoded_members_sha256']),retry.FIRST_MEMBERS)
                with log.open('ab') as stream:stream.write(b'changed evidence')
                with self.assertRaises(ValueError):retry.inspect_first_evidence(api,archive,log,root/'changed-log',prior)

    def test_coherently_rehashed_partial_outputs_cannot_hide_missing_members_or_failed_source_controls(self):
        changes=[lambda files:files['original-stock-audit-controls.json'].update(tests_run=175),
            lambda files:files['original-stock-audit-controls.json'].update(sources_match_producer=False),
            lambda files:files.update({'original-stock-audit/independent/fake-passed-audit.json':{'status':'passed'}})]
        for change in changes:
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);archive,log,pins=self.evidence(root,change)
                with patch.multiple(retry,**pins):
                    with self.assertRaises(ValueError):retry.inspect_first_evidence(self.api(),archive,log,root/'decoded',prior)

    def test_only_the_exact_known_BOM_elision_is_accepted_and_observed_bytes_are_never_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);text=b'exact immutable first-job text\n';original=b'\xef\xbb\xbf'+text
            full=root/'original.log';wire=root/'text-decoded.log';full.write_bytes(original);wire.write_bytes(text)
            with patch.multiple(retry,FIRST_LOG_SIZE=len(original),FIRST_LOG_DIGEST=hashlib.sha256(original).hexdigest(),
                                FIRST_LOG_TEXT_SIZE=len(text),FIRST_LOG_TEXT_DIGEST=hashlib.sha256(text).hexdigest()):
                a,meta_a=retry.log_identity(full);b,meta_b=retry.log_identity(wire)
                self.assertEqual(a,b);self.assertEqual(a,original)
                self.assertFalse(meta_a['known_leading_UTF8_BOM_elision']);self.assertTrue(meta_b['known_leading_UTF8_BOM_elision'])
                self.assertFalse(meta_b['input_file_rewritten']);self.assertFalse(meta_b['API_attempt_or_capture_bytes_modified'])
                self.assertEqual(wire.read_bytes(),text);self.assertEqual(full.read_bytes(),original)
                for changed in (b' '+text,text.replace(b'\n',b'\r\n'),text+b'changed'):
                    wire.write_bytes(changed)
                    with self.assertRaises(ValueError):retry.log_identity(wire)

    def test_old_source_guard_and_complete_608_member_safety_and_reference_receipt_bodies_are_unchanged(self):
        old=Path(prior.__file__).read_bytes().replace(b'\r\n',b'\n')
        self.assertEqual(hashlib.sha256(old).hexdigest(),'b82e501c920ef0ee3006acbecc0627ff703a28761ea6d5d58e57ca2091d2724b')
        def body(path,name):
            return ast.dump(next(n for n in ast.parse(Path(path).read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name==name),include_attributes=False)
        for name in ('audit_receipts','bind_artifacts','extract'):
            self.assertEqual(body(prior.__file__,name),body(restored.__file__,name))


if __name__=='__main__':unittest.main()
