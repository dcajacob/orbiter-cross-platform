"""Full and one-profile published rejection archives retain their exact actual outer namespace and API scope."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import inspect_published_class_rejections as replay


class RejectionReplayNamespaceTests(unittest.TestCase):
    def test_repository_root_outer_members_are_preserved_without_relabelling_original_inner_paths(self):
        profile='Debug-sse2';names=['out/hosted-native-class-rejections/'+profile+'/'+n for n in ('collection.json','raw-index.json','raw-original-inputs.tar.gz','original-rejections-audit.json','original-SDK-header-restoration.json','original-fixture-SDK.json','original-Windows-PE.json')]
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp)/'actual.zip'
            with zipfile.ZipFile(archive,'w') as z:
                for n in names:z.writestr(n,b'actual original body')
            payload=Path(tmp)/'decoded';members=replay.restore_outer(archive,payload,profile)
            self.assertEqual(set(members),set(names));self.assertEqual((payload/names[0]).read_bytes(),b'actual original body')
            self.assertFalse((payload/'hosted-native-class-rejections').exists())

    def test_only_explicit_completed_two_job_single_profile_trial_can_use_trial_protocol(self):
        lock=json.loads((Path(__file__).with_name('class-rejection-compiler-trial-inputs-v1.lock.json')).read_text());profile='Debug-sse2';pin=lock['profiles'][profile];source=lock['source']
        api=dict(repository=lock['repository'],run=dict(repository=dict(private=False,full_name='dcajacob/orbiter-cross-platform'),id=lock['run_id'],head_sha=source,head_branch=lock['branch'],path=lock['workflow'],run_attempt=1,status='completed'),jobs=[dict(id=int(i),name=n,run_id=lock['run_id'],head_sha=source,labels=['ubuntu-24.04'],status='completed',conclusion='success') for i,n in lock['jobs'].items()],artifact=dict(id=pin['artifact_id'],name='original-class-normal-host-rejection-controls-'+profile,expired=False,size_in_bytes=pin['archive_bytes'],digest='sha256:'+pin['archive_sha256'],workflow_run=dict(id=lock['run_id'],head_sha=source)))
        replay.validate_api(api,lock,profile)
        for change in (lambda a:a['jobs'][1].update(conclusion='failure'),lambda a:a['jobs'].pop(),lambda a:a['artifact'].update(digest='sha256:'+'0'*64)):
            value=copy.deepcopy(api);change(value)
            with self.assertRaises(ValueError):replay.validate_api(value,lock,profile)
        broader=copy.deepcopy(lock);broader['profiles']['Release-sse2']=dict(pin)
        with self.assertRaises(ValueError):replay.validate_api(api,broader,profile)
