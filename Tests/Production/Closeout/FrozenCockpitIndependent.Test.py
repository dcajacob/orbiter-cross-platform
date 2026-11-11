import tempfile
from pathlib import Path
from unittest import TestCase
from contracts import PROFILES,atomic_json
from audit_frozen_cockpit_component import RUN,SOURCE,restore_original


class FrozenCockpitIndependent(TestCase):
    def api(self):
        return dict(run=dict(id=RUN,head_sha=SOURCE,head_branch='qualification/frozen-core-cockpit-v2',path='.github/workflows/phase6-frozen-core-cockpit.yml',
            run_attempt=1,status='completed',conclusion='success',repository=dict(private=False,full_name='dcajacob/orbiter-cross-platform')),
            jobs=[dict(name=n,head_sha=SOURCE,run_id=RUN,status='completed',conclusion='success',labels=['ubuntu-24.04']) for n in ['controls',*['Frozen core cockpit '+p for p in PROFILES]]],
            artifact=dict(name='frozen-core-cockpit-Debug-automatic-raw',expired=False,workflow_run=dict(id=RUN,head_sha=SOURCE),size_in_bytes=1,digest='sha256:'+'0'*64))

    def reject(self,api):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);atomic_json(base/'api.json',api);(base/'producer.zip').write_bytes(b'x')
            with self.assertRaises(ValueError):restore_original('Debug-automatic',base)
            self.assertFalse((base/'selected-raw').exists())

    def test_original_failed_job_cannot_be_relabelled_as_completed_component(self):
        api=self.api();api['run']['conclusion']='failure';self.reject(api)

    def test_one_profile_or_source_control_cannot_substitute_for_all_completed_jobs(self):
        api=self.api();api['jobs'].pop();self.reject(api)

    def test_forged_raw_archive_digest_is_rejected_before_restoration(self):
        self.reject(self.api())
