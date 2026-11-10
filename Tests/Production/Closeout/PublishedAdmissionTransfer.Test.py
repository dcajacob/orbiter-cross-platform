from copy import deepcopy
from unittest import TestCase
import restore_published_admission_reference as ref


class PublishedAdmissionTransfer(TestCase):
    def fixture(self):
        run=dict(id=ref.RUN,head_sha=ref.SOURCE,run_attempt=1,head_branch='qualification/frozen-normal-admission-v1',
                 path='.github/workflows/phase6-frozen-normal-admission.yml',status='completed',conclusion='failure',
                 repository=dict(full_name=ref.REPO,private=False))
        jobs=[dict(id=i,conclusion=c,name=n,run_id=ref.RUN,head_sha=ref.SOURCE,run_attempt=1,status='completed',
                   labels=['ubuntu-24.04'],steps=[dict(name=ref.FAILED_STEP,conclusion='failure')] if c=='failure' else [])
              for n,(i,c) in ref.JOBS.items()]
        artifact=dict(id=ref.ARTIFACT,name='frozen-normal-admission-reference',size_in_bytes=ref.ZIP_BYTES,
                      digest='sha256:'+ref.ZIP_SHA,expired=False,workflow_run=dict(id=ref.RUN,head_sha=ref.SOURCE))
        return run,jobs,artifact

    def test_same_existing_reference_can_exceed_obsolete_memory_bound(self):
        ref.inspect_api(*self.fixture())
        self.assertGreater(ref.ZIP_BYTES,512*1024**2)

    def test_origin_digest_size_and_failed_states_cannot_be_normalized(self):
        run,jobs,artifact=self.fixture()
        for changed in (dict(size_in_bytes=ref.ZIP_BYTES+1),dict(digest='sha256:'+'0'*64),dict(expired=True)):
            with self.assertRaisesRegex(ValueError,'Exact original successful prerequisite'):
                ref.inspect_api(run,jobs,artifact|changed)
        with self.assertRaisesRegex(ValueError,'Original failed run history'):
            ref.inspect_api(run|dict(conclusion='success'),jobs,artifact)

    def test_prior_actual_profile_failure_must_be_only_transport(self):
        run,jobs,artifact=self.fixture();broken=deepcopy(jobs)
        broken[-1]['steps'].append(dict(name='simulator execution',conclusion='failure'))
        with self.assertRaisesRegex(ValueError,'Only original failed reference transfer'):
            ref.inspect_api(run,broken,artifact)
