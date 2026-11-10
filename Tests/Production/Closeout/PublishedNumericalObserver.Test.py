from unittest import TestCase
import copy
import inspect_published_numerical_observers as audit


class PublishedNumericalObserver(TestCase):
    def fixture(self):
        p=dict(run_id=99,source='a'*40,branch='qualification/example',job_id=101,artifact_id=103,archive_bytes=123,archive_sha256='b'*64)
        r=dict(repository=dict(private=False,full_name='dcajacob/orbiter-cross-platform'),id=99,head_sha='a'*40,head_branch=p['branch'],path='.github/workflows/phase6-native-numerical-observer-equivalence.yml',run_attempt=1,status='completed',conclusion='success')
        j=dict(id=101,run_id=99,head_sha='a'*40,status='completed',conclusion='success',labels=['ubuntu-24.04'])
        a=dict(id=103,name='original-save-numerical-observer-three-world-full-raw',size_in_bytes=123,digest='sha256:'+'b'*64,expired=False,workflow_run=dict(id=99,head_sha='a'*40))
        return dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),run=r,jobs=[j],artifact=a),p

    def test_failed_partial_or_foreign_source_cannot_qualify(self):
        api,pin=self.fixture();audit.validate_api(api,pin)
        for key,value in [('head_sha','c'*40),('status','in_progress'),('conclusion','failure'),('run_attempt',2)]:
            wrong=copy.deepcopy(api);wrong['run'][key]=value
            with self.assertRaises(ValueError):audit.validate_api(wrong,pin)

    def test_unbound_corrupt_or_expired_archive_is_rejected(self):
        api,pin=self.fixture()
        for key,value in [('id',104),('size_in_bytes',124),('digest','sha256:'+'c'*64),('expired',True)]:
            wrong=copy.deepcopy(api);wrong['artifact'][key]=value
            with self.assertRaises(ValueError):audit.validate_api(wrong,pin)
        wrong=copy.deepcopy(api);wrong['artifact']['workflow_run']['head_sha']='c'*40
        with self.assertRaises(ValueError):audit.validate_api(wrong,pin)

    def test_missing_duplicate_failed_or_nonstandard_jobs_are_rejected(self):
        api,pin=self.fixture()
        for jobs in ([],api['jobs']*2,[dict(api['jobs'][0],conclusion='failure')],[dict(api['jobs'][0],labels=['self-hosted'])]):
            wrong=copy.deepcopy(api);wrong['jobs']=jobs
            with self.assertRaises(ValueError):audit.validate_api(wrong,pin)
