"""Disposable proof fixtures only; immutable source/API pins remain required in production."""
import ast
import contextlib
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from contracts import ROOT

HOSTED=ROOT/'Tests/Production/CurrentWindows/Hosted';sys.path.insert(0,str(HOSTED))
import source_complete_retry_provider as provider
import source_complete_retry_worker as worker
import prepare_source_complete_retry_request as request
import execute_source_complete_retry_phase as execution
import retry_reference_proof as proof
import audit_retry_lineage as retry
import restore_source_complete_reference as prior


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


old=module('retry_current_old_fixtures',ROOT/'Tests/Production/Closeout/SourceCompleteCurrent.Test.py')
history=module('retry_current_history_fixtures',ROOT/'Tests/Production/Closeout/AuditRetryLineage.Test.py')


class CurrentAuditRetryTests(unittest.TestCase):
    @contextlib.contextmanager
    def evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);out=root/'out';api=out/'reference-api';api.mkdir(parents=True)
            first,log,pins=history.ExactOriginalAuditRetryTests().evidence(root)
            shutil.copy2(first,api/'first.zip');shutil.copy2(log,api/'first-job.log')
            with zipfile.ZipFile(first) as source:
                files={n:source.read(n) for n in source.namelist()}
            manifest=json.loads(files['original-stock-audit/transport/download.json'])
            original=json.loads(files['original-stock-audit/api-records.json'])
            _,writer,cohort=old.reference_fixture.SourceCompleteReferenceTests().receipts()
            msha=hashlib.sha256(files['original-stock-audit/transport/download.json']).hexdigest()
            writer['download_manifest_sha256']=msha;wbody=json.dumps(writer).encode()
            cohort.update(transport_sha256=msha,writer_audit_sha256=hashlib.sha256(wbody).hexdigest());cbody=json.dumps(cohort).encode()
            files['original-stock-audit/independent/writer-audit.json']=wbody
            files['original-stock-audit/independent/original-persistence-audit.json']=cbody
            with zipfile.ZipFile(api/'audit.zip','w') as source:
                for name,body in files.items():source.writestr(name,body)
            pins.update(RETRY_SIZE=(api/'audit.zip').stat().st_size,RETRY_DIGEST=proof.sha(api/'audit.zip'))
            with patch.multiple(retry,**pins):
                first_api=history.ExactOriginalAuditRetryTests().api();success_api=history.ExactOriginalAuditRetryTests().api(2)
                for name,value in [('first',first_api),('audit',success_api),('original',original)]:
                    (api/(name+'.json')).write_text(json.dumps(value))
                base=out/'reference-audit-restoration';base.mkdir()
                lineage=retry.inspect_first_evidence(first_api,api/'first.zip',api/'first-job.log',base/'first-attempt-source-artifact',prior)
                lineage.update(first_attempt_api_sha256=proof.sha(api/'first.json'),successful_attempt=2,
                    successful_job_id=retry.RETRY_JOB,successful_artifact_id=retry.RETRY_ARTIFACT,successful_artifact_sha256='sha256:'+retry.RETRY_DIGEST)
                prior.extract(api/'audit.zip',base/'source-artifact')
                members=prior.transport.legacy.inspect_archive(api/'audit.zip',base/'source-artifact',retry.RETRY_DIGEST,retry.RETRY_SIZE)
                paths={'reference_transport':out/'original-stock-audit/transport/download.json',
                    'reference_audit':out/'original-stock-audit/independent/writer-audit.json',
                    'reference_persistence_audit':out/'original-stock-audit/independent/original-persistence-audit.json',
                    'reference_restoration':base/'restoration.json'}
                for name,body in [('reference_transport',files['original-stock-audit/transport/download.json']),('reference_audit',wbody),('reference_persistence_audit',cbody)]:
                    paths[name].parent.mkdir(parents=True,exist_ok=True);paths[name].write_bytes(body)
                restored=dict(protocol='phase6-source-complete-original-reference-retry-restoration-v3',
                    status='restored-exact-original-cohort-after-verified-audit-retry-only',original_capture_source=request.ORIGINAL,
                    original_auditor_source=request.AUDITOR,restorer_source='e'*40,original_windows_processes=608,
                    original_api_archive_bindings={p:dict(fixture_only=True) for p in prior.PROFILES},
                    original_saves_relabelled=False,current_or_native_qualification_granted=False,phase6_complete=False,native_admission_qualified=False,
                    audit_retry_lineage=lineage,successful_audit_decoded_members_sha256=members,
                    source_audit_api_sha256=proof.sha(api/'audit.json'),actual_reference_api_sha256=proof.sha(api/'original.json'),
                    original_audit_run_id=retry.RUN,original_audit_artifact_id=retry.RETRY_ARTIFACT,original_audit_archive_sha256='sha256:'+retry.RETRY_DIGEST,
                    original_transport_sha256=proof.sha(paths['reference_transport']),original_writer_audit_sha256=proof.sha(paths['reference_audit']),
                    original_cohort_audit_sha256=proof.sha(paths['reference_persistence_audit']))
                paths['reference_restoration'].write_text(json.dumps(restored))
                cfg=dict(roles=dict(runner=dict(commit='e'*40)),reference_retry_inputs=proof.inventory(out),
                    **{name:dict(path=str(path),sha256=proof.sha(path)) for name,path in paths.items()})
                yield out,cfg,restored,manifest

    def test_both_real_attempts_all_original_receipts_and_raw_partial_outputs_are_reverified(self):
        with self.evidence() as (out,cfg,restored,manifest):
            before=copy.deepcopy(cfg);result=provider.reference_receipts(cfg)
            self.assertEqual(cfg,before);self.assertTrue(result['actual_retry_proof_inputs_independently_reverified'])
            self.assertEqual(result['original_windows_processes'],608)
            self.assertFalse(result['current_or_native_qualification_granted']);self.assertFalse(result['phase6_complete'])
            self.assertEqual(result['audit_retry_lineage']['first_attempt'],1);self.assertEqual(result['audit_retry_lineage']['successful_attempt'],2)
            self.assertEqual(proof.guarded(cfg),{v['path']:v['sha256'] for v in cfg['reference_retry_inputs'].values()})

    def test_coherent_rehash_cannot_change_retry_attempt_or_raw_first_zip_or_preserved_partial_member(self):
        for name,change in [
            ('reference-api/first.json',lambda path:path.write_text(json.dumps(dict(json.loads(path.read_text()),run=dict(json.loads(path.read_text())['run'],run_attempt=2))))),
            ('reference-api/first.zip',lambda path:path.write_bytes(path.read_bytes()+b'changed API ZIP')),
            ('reference-audit-restoration/first-attempt-source-artifact/original-stock-audit-controls.json',lambda path:path.write_text(path.read_text()+' ')),
            ('reference-api/audit.json',lambda path:path.write_text(json.dumps(dict(json.loads(path.read_text()),artifact=dict(json.loads(path.read_text())['artifact'],id=retry.RETRY_ARTIFACT+1)))))
        ]:
            with self.evidence() as (out,cfg,restored,manifest):
                path=out/name;change(path);cfg['reference_retry_inputs'][name]['sha256']=proof.sha(path)
                with self.assertRaises(ValueError):proof.verify(cfg,restored,manifest)

    def test_missing_members_changed_bytes_and_claimed_lineage_cannot_pass(self):
        for mode in ('missing','bytes','lineage'):
            with self.evidence() as (out,cfg,restored,manifest):
                if mode=='missing':cfg['reference_retry_inputs'].pop('reference-api/first-job.log')
                elif mode=='bytes':(out/'reference-api/first-job.log').write_bytes(b'new log')
                else:restored['audit_retry_lineage']['first_attempt']=2
                with self.assertRaises(ValueError):proof.verify(cfg,restored,manifest)

    def test_complete_scope_exact_phase_name_and_inherited_workspace_paths_remain_required(self):
        cfg,config=old.scope_fixture.HostedStockProviderTests().config();cfg.update(transport_protocol=provider.PROTOCOL,name='Debug-automatic-stock',reference_retry_inputs={
            'reference-api/audit.json':dict(path=cfg['workspace']+'/out/reference-api/audit.json',sha256='a'*64)})
        self.assertEqual(provider.selection(cfg,config),(config['cases'],False))
        for change in (lambda c:c.update(name='collector.py'),lambda c:c.update(transport_protocol=old.provider.PROTOCOL),
                       lambda c:c.update(scene_workers=2),lambda c:c.update(desktop='private-claim'),
                       lambda c:c['reference_retry_inputs']['reference-api/audit.json'].update(path='D:/outside/audit.json')):
            changed=copy.deepcopy(cfg);change(changed)
            with self.assertRaises(ValueError):provider.selection(changed,config)

    def test_unchanged_real_process_completion_and_exact_saved_input_controls_are_retained(self):
        cfg,result=old.phase_fixture.HostedStockPhaseTests().worker();cfg['transport_protocol']=result['transport_protocol']=provider.PROTOCOL
        execution.terminal(cfg,result,99,'b'*64,'a'*64)
        result['actual_process_receipts'][0]['timing']['actual_returncode']=1
        with self.assertRaises(ValueError):execution.terminal(cfg,result,99,'b'*64,'a'*64)
        original=old.phase_fixture.request
        try:
            old.phase_fixture.request=request
            old.phase_fixture.HostedStockPhaseTests().test_saved_input_selection_retains_both_exact_repeats_for_every_original_case()
        finally:old.phase_fixture.request=original

    def test_original_capture_body_terminal_and_paired_input_algorithms_remain_identical(self):
        self.assertEqual(worker.prepared_body().replace('from source_complete_retry_provider import','from source_complete_provider import'),old.worker.prepared_body())
        def body(path,name):return ast.dump(next(n for n in ast.parse(Path(path).read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name==name),include_attributes=False)
        self.assertEqual(body(request.__file__,'paired_inputs'),body(old.request.__file__,'paired_inputs'))
        self.assertEqual(body(execution.__file__,'terminal'),body(old.execution.__file__,'terminal'))
        for name,checksum in {'source_complete_provider.py':'df70acd47a4a12400ecb9dd0afacbc379e8d190aa8b8bfb55126536f890de2c5',
            'prepare_source_complete_request.py':'62f83c7c6321b81150350cc7b7ce6f387cec5caa311d6b7eca7ada78f610330a',
            'source_complete_worker.py':'6a0bee9e75ff217caf3cfe08c8c21c4c81fc1f6b1f3dbb1d120466ee99ae6a7c',
            'execute_source_complete_phase.py':'fed4675857cb926bff349f99cdc60c7401b15633607e04c3fd8c1c24e69af0b7'}.items():
            self.assertEqual(hashlib.sha256((HOSTED/name).read_bytes()).hexdigest(),checksum)


if __name__=='__main__':unittest.main()
