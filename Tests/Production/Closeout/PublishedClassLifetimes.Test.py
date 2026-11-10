"""Bounded publication controls; never run a simulator or grant a class facet."""
import copy
import json
from pathlib import Path
import tempfile
import stat
import subprocess
import warnings
import unittest
import zipfile
from contracts import ROOT
import inspect_hosted_class_lifetimes as published


class PublishedClassLifetimesTests(unittest.TestCase):
    def fixture(self):
        return json.loads((ROOT/'Tests/Production/Closeout/class-lifetime-producer-api.fixture.json').read_text())

    def test_completed_selected_profile_preserves_other_actual_live_or_failed_states(self):
        fixture=self.fixture();self.assertFalse(fixture['qualification_granted']);published.validate_api(fixture,'Debug-sse2')
        other=next(j for j in fixture['jobs'] if j['id']==129543903611)
        other.update(status='completed',conclusion='failure')
        fixture['run'].update(status='completed',conclusion='failure')
        published.validate_api(fixture,'Debug-sse2')
        self.assertEqual(other['conclusion'],'failure')

    def test_wrong_source_active_selected_missing_job_and_wrong_digest_are_rejected(self):
        changes=[lambda r:r['run'].update(head_sha='f'*40),
                 lambda r:next(j for j in r['jobs'] if j['id']==129543903705).update(status='in_progress',conclusion=None),
                 lambda r:r['jobs'].pop(),
                 lambda r:r['artifact'].update(digest='sha256:'+'0'*64),
                 lambda r:r['jobs'][0].update(labels=['self-hosted'])]
        for change in changes:
            fixture=self.fixture();change(fixture)
            with self.assertRaises(ValueError):published.validate_api(fixture,'Debug-sse2')

    def test_uncompleted_profile_and_archive_escape_cannot_be_reused(self):
        with self.assertRaisesRegex(ValueError,'already-completed'):published.validate_api(self.fixture(),'Release-sse2')
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);archive=base/'bad.zip'
            with zipfile.ZipFile(archive,'w') as output:output.writestr('../escape',b'bad')
            with self.assertRaisesRegex(ValueError,'Unsafe'):
                published.restore_archive(archive,base/'payload','Debug-sse2',base/'owner')
            self.assertFalse((base/'escape').exists())

    def test_original_paused_source_uses_actual_guarded_bytes_without_inventing_fields(self):
        source=published.load(published.LOCK)['source']
        family=dict(producer_commit=source,runtime_owner=str(ROOT))
        paused=dict(guarded_files_sha256={})
        for relative in ('Tests/Production/RemainingVessels/paused_attachments.py',
                         'Tests/Production/Closeout/hosted_class_lifetimes.py'):
            body=subprocess.check_output(['git','-C',str(ROOT),'show',source+':'+relative])
            paused['guarded_files_sha256'][str(ROOT/relative)]=published.hashlib.sha256(body).hexdigest()
        before=copy.deepcopy(paused)
        published.verify_capture_sources(family,paused,source)
        self.assertEqual(paused,before);self.assertNotIn('producer_commit',paused)
        paused['guarded_files_sha256'].clear()
        with self.assertRaises(ValueError):published.verify_capture_sources(family,paused,source)

    def test_every_member_is_restored_and_duplicate_link_or_overwrite_rejected(self):
        profile='Debug-sse2'
        names=['native-class-lifetimes/'+profile+'/lifetimes.json','native-class-paused/'+profile+'/verification.json',
               'hosted-native-class-lifetimes/'+profile+'/collection.json']
        for damage in (None,'duplicate','symlink','overwrite'):
            with self.subTest(damage=damage),tempfile.TemporaryDirectory() as temp:
                base=Path(temp);archive=base/'capture.zip';owner=base/'owner';owner.mkdir()
                with zipfile.ZipFile(archive,'w') as output,warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    for name in names:output.writestr(name,b'original')
                    output.writestr('extra-original.log',b'original extra')
                    if damage=='duplicate':output.writestr(names[0],b'changed')
                    if damage=='symlink':
                        item=zipfile.ZipInfo('link');item.create_system=3;item.external_attr=(stat.S_IFLNK|0o777)<<16
                        output.writestr(item,b'/tmp/escape')
                if damage=='overwrite':
                    target=owner/'out'/names[0];target.parent.mkdir(parents=True);target.write_bytes(b'keep existing')
                if damage:
                    with self.assertRaises(ValueError):published.restore_archive(archive,base/'payload',profile,owner)
                    if damage=='overwrite':self.assertEqual(target.read_bytes(),b'keep existing')
                else:
                    files,materialized=published.restore_archive(archive,base/'payload',profile,owner)
                    self.assertEqual(len(files),4);self.assertEqual(len(materialized),3)
                    for name in names:self.assertEqual((owner/'out'/name).read_bytes(),b'original')
