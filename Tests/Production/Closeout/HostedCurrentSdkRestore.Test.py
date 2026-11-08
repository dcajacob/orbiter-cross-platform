"""Reject mixed current SDK producers and incomplete or unsafe runtime restoration."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from contracts import ROOT

sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
from restore_sdk import validate_api,unpack,PRODUCER,RUN,PINS,REQUIRED_STEPS


class HostedCurrentSdkRestoreTests(unittest.TestCase):
    def record(self,configuration='Debug'):
        ident,size,digest=PINS[configuration]
        return dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),
            run=dict(id=RUN,head_sha=PRODUCER,head_branch='qualification/current-windows-sdk-retry',
                     path='.github/workflows/phase6-current-windows-sdk.yml',run_attempt=1,status='completed',conclusion='success'),
            artifact=dict(id=ident,name='current-windows-sdk-'+configuration,expired=False,size_in_bytes=size,digest='sha256:'+digest,
                          workflow_run=dict(id=RUN,head_sha=PRODUCER)),
            jobs=[dict(id=1,name='current-windows / Real Windows client '+configuration+' x64',run_id=RUN,head_sha=PRODUCER,
                       status='completed',conclusion='success',labels=['windows-2025'],
                       steps=[dict(name=n,status='completed',conclusion='success') for n in REQUIRED_STEPS]),
                  dict(id=128875554076,run_id=RUN,head_sha=PRODUCER,status='completed',conclusion='success',name='comparison')])

    def test_actual_completed_sdk_and_comparison_roles_are_bound(self):
        for configuration in PINS:self.assertEqual(validate_api(self.record(configuration),configuration)['id'],1)
        for change in (lambda r:r['run'].update(head_sha='b'*40),lambda r:r['run'].update(run_attempt=2),
                       lambda r:r['run'].update(conclusion='failure'),lambda r:r['artifact'].update(digest='sha256:'+'a'*64),
                       lambda r:r['artifact'].update(size_in_bytes=1),lambda r:r['jobs'][0]['steps'][0].update(conclusion='skipped'),
                       lambda r:r['jobs'][0].update(labels=['windows-2022']),lambda r:r['jobs'][1].update(conclusion='failure'),
                       lambda r:r['jobs'].append(copy.deepcopy(r['jobs'][0]))):
            record=self.record();change(record)
            with self.assertRaises(ValueError):validate_api(record,'Debug')

    def test_restored_runtime_bytes_must_match_the_complete_inner_seal(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);archive=root/'runtime.zip';body=b'fixture-only-sdk'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('Orbitersdk/include/fixture.h',body)
            expected={'Orbitersdk/include/fixture.h':hashlib.sha256(body).hexdigest()}
            self.assertEqual(unpack(archive,root/'good',expected),expected)
            for index,changed in enumerate(({},expected|{'missing.dll':'b'*64},{next(iter(expected)):'c'*64})):
                with self.assertRaises(ValueError):unpack(archive,root/('bad-'+str(index)),changed)
            with self.assertRaises(ValueError):unpack(archive,root/'good',expected)

    def test_archive_paths_and_case_collisions_cannot_change_other_inputs(self):
        for names in (('../outside',),('folder/./alias',),('C:/outside',),('file.dll','FILE.dll')):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);archive=root/'runtime.zip'
                with zipfile.ZipFile(archive,'w') as z:
                    for name in names:z.writestr(name,b'fixture-only')
                with self.assertRaises(ValueError):unpack(archive,root/'output')
                self.assertFalse((root/'outside').exists())


if __name__=='__main__':unittest.main()
