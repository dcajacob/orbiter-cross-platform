"""Independent raw rejection replay keeps every actual source, profile, symbol and audit guard."""
import copy
from pathlib import Path
import tempfile
import unittest
import zipfile
import inspect_published_class_rejections as replay


class PublishedClassRejectionsTests(unittest.TestCase):
    def fixture(self):
        profiles=('Debug-automatic','Debug-sse2','Release-automatic','Release-sse2');jobs={str(i+11):'capture '+p for i,p in enumerate(profiles)};jobs['10']='readiness';source='a'*40
        pin=dict(job_id=11,artifact_id=21,archive_bytes=100,archive_sha256='b'*64)
        lock=dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),run_id=1,source=source,branch='qualification/actual-original',workflow='.github/workflows/original.yml',jobs=jobs,readiness_job_id=10,profiles={'Debug-automatic':pin})
        run=dict(repository=dict(private=False,full_name='dcajacob/orbiter-cross-platform'),id=1,head_sha=source,head_branch=lock['branch'],path=lock['workflow'],run_attempt=1,status='in_progress')
        api=dict(repository=lock['repository'],run=run,jobs=[dict(id=int(i),name=name,run_id=1,head_sha=source,labels=['ubuntu-24.04'],status='completed' if i in ('10','11') else 'in_progress',conclusion='success' if i in ('10','11') else None) for i,name in jobs.items()],artifact=dict(id=21,name='original-class-normal-host-rejection-controls-Debug-automatic',expired=False,size_in_bytes=100,digest='sha256:'+'b'*64,workflow_run=dict(id=1,head_sha=source)))
        return api,lock

    def test_only_completed_selected_original_profile_is_replayed_while_other_work_remains_live(self):
        api,lock=self.fixture();self.assertEqual(replay.validate_api(api,lock,'Debug-automatic'),lock['profiles']['Debug-automatic'])
        self.assertEqual(api['run']['status'],'in_progress');self.assertEqual(api['jobs'][1]['status'],'in_progress')

    def test_changed_source_archive_runner_roster_failed_or_incomplete_profile_cannot_pass(self):
        mutations=(lambda a:a['run'].update(head_sha='c'*40),lambda a:a['artifact'].update(digest='sha256:'+'c'*64),lambda a:a['jobs'][0].update(labels=['self-hosted']),lambda a:a['jobs'].pop(),lambda a:next(j for j in a['jobs'] if j['id']==11).update(status='in_progress',conclusion=None),lambda a:next(j for j in a['jobs'] if j['id']==10).update(conclusion='failure'))
        for mutation in mutations:
            api,lock=self.fixture();mutation(api)
            with self.assertRaises(ValueError):replay.validate_api(api,lock,'Debug-automatic')

    def test_only_sdk_operation_flag_and_raw_tool_formatting_can_differ_symbols_and_identity_stay_exact(self):
        old=dict(header_was_present=False,header_sha256='a'*64,native_module_SDK_roles={'delegate':dict(metadata=dict(defined=['OrbiterNativeQuery'],undefined=['OrbiterNativeAtlantisQuery'],needed=['liborbiter_native_atlantis.so'],commands=dict(defined=dict(argv=['nm','-D','--defined-only','original.so'],actual_returncode=0,stdout_sha256='b'*64,stderr_sha256='c'*64))))})
        fresh=copy.deepcopy(old);fresh['header_was_present']=True;fresh['native_module_SDK_roles']['delegate']['metadata']['commands']['defined']['stdout_sha256']='d'*64
        self.assertEqual(replay.semantic_sdk(old),replay.semantic_sdk(fresh))
        for mutate in (lambda a:a.update(header_sha256='e'*64),lambda a:a['native_module_SDK_roles']['delegate']['metadata'].update(defined=[]),lambda a:a['native_module_SDK_roles']['delegate']['metadata'].update(needed=['wrong.so'])):
            changed=copy.deepcopy(fresh);mutate(changed);self.assertNotEqual(replay.semantic_sdk(old),replay.semantic_sdk(changed))
        fresh['native_module_SDK_roles']['delegate']['metadata']['commands']['defined']['actual_returncode']=1
        with self.assertRaises(ValueError):replay.semantic_sdk(fresh)

    def test_outer_raw_metadata_cannot_escape_or_omit_original_audit_or_lossless_inputs(self):
        for name in ('../escaped','/absolute','a\\b','a:b','incomplete-only.json'):
            with tempfile.TemporaryDirectory() as temp:
                archive=Path(temp)/'input.zip'
                with zipfile.ZipFile(archive,'w') as z:z.writestr(name,b'original')
                with self.assertRaises(ValueError):replay.restore_outer(archive,Path(temp)/'decoded','Debug-automatic')
