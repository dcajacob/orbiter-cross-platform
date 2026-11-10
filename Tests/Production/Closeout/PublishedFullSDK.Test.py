"""Negative publication/source controls; no simulator or complete class acceptance credit."""
import copy
import json
from pathlib import Path
import tempfile
import zipfile
import stat
import warnings
import unittest
from contracts import ROOT
import verify_published_full_SDK as published


class PublishedFullSDKTests(unittest.TestCase):
    def fixture(self):
        return json.loads((ROOT/'Tests/Production/Closeout/published-full-SDK-api.fixture.json').read_text())

    def test_actual_complete_selected_cohort_and_all_other_job_states_are_preserved(self):
        value=self.fixture();before=copy.deepcopy(value)
        published.validate_api(value,'automatic');self.assertEqual(value,before)
        other=next(j for j in value['jobs'] if j['id']==129642687877)
        other.update(status='completed',conclusion='failure');value['run'].update(status='completed',conclusion='failure')
        published.validate_api(value,'automatic');self.assertEqual(other['conclusion'],'failure')
        lock,pin=published.validate_api(value,'automatic');self.assertEqual(pin['archive_bytes'],6871868)
        self.assertEqual(set(lock['cohorts']),{'automatic','sse2'})

    def test_wrong_source_active_selection_digest_runner_or_missing_roster_cannot_verify(self):
        changes=(lambda v:v['run'].update(head_sha='f'*40),lambda v:v['run'].update(status='unknown'),
                 lambda v:v['jobs'].pop(),lambda v:v['jobs'][0].update(labels=['self-hosted']),
                 lambda v:next(j for j in v['jobs'] if j['id']==129642687472).update(status='in_progress',conclusion=None),
                 lambda v:v['artifact'].update(expired=True),lambda v:v['artifact'].update(digest='sha256:'+'0'*64),
                 lambda v:v['artifact']['workflow_run'].update(head_sha='e'*40))
        for mutate in changes:
            value=self.fixture();mutate(value)
            with self.assertRaises(ValueError):published.validate_api(value,'automatic')
        with self.assertRaises(ValueError):published.validate_api(self.fixture(),'unknown')

    def test_complete_member_hashes_and_unsafe_duplicate_or_symlink_archive_are_guarded(self):
        for damage in (None,'escape','duplicate','symlink'):
            with self.subTest(damage=damage),tempfile.TemporaryDirectory() as temp:
                p=Path(temp)/'metadata.zip'
                with zipfile.ZipFile(p,'w') as out,warnings.catch_warnings():
                    warnings.simplefilter('ignore');out.writestr('source.py',b'original source');out.writestr('proof.json',b'{}')
                    if damage=='escape':out.writestr('../outside',b'bad')
                    if damage=='duplicate':out.writestr('source.py',b'changed')
                    if damage=='symlink':
                        entry=zipfile.ZipInfo('link');entry.create_system=3;entry.external_attr=(stat.S_IFLNK|0o777)<<16;out.writestr(entry,b'/tmp/outside')
                if damage:
                    with self.assertRaises(ValueError):published.inspect_members(p)
                else:
                    members,bodies=published.inspect_members(p);self.assertEqual(len(members),2)
                    self.assertEqual(bodies['source.py'],b'original source')
                    self.assertEqual(members['source.py']['sha256'],published.hashlib.sha256(b'original source').hexdigest())
