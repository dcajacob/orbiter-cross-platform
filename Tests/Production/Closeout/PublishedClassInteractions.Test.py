"""Complete published interaction provenance and lossless bounded restoration controls."""
import copy
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contracts import ROOT
import inspect_published_class_interactions as published


class PublishedClassInteractionsTests(unittest.TestCase):
    def fixture(self):return json.loads((ROOT/'Tests/Production/Closeout/published-class-interaction-api.fixture.json').read_text())

    def test_exact_selected_completed_source_artifact_and_standard_roster_required_without_relabelling_other_profiles(self):
        record=self.fixture();before=copy.deepcopy(record);lock,pin=published.validate_api(record,'Debug-automatic')
        self.assertEqual(record,before);self.assertEqual(pin['artifact_id'],13745302649);self.assertEqual(pin['archive_bytes'],3008231142)
        for mutate in (lambda r:r['jobs'].pop(),lambda r:r['jobs'][0].update(conclusion='failure'),
                       lambda r:next(j for j in r['jobs'] if j['id']==129679052887).update(status='in_progress'),
                       lambda r:r['jobs'][0].update(labels=['self-hosted']),lambda r:r['run'].update(head_sha='e'*40),
                       lambda r:r['run']['repository'].update(private=True),lambda r:r['artifact'].update(size_in_bytes=1),
                       lambda r:r['artifact'].update(expired=True),lambda r:r['artifact'].update(digest='sha256:'+'0'*64)):
            value=copy.deepcopy(record);mutate(value)
            with self.assertRaises(ValueError):published.validate_api(value,'Debug-automatic')
        value=copy.deepcopy(record);next(j for j in value['jobs'] if j['id']==129679052719).update(status='completed',conclusion='failure')
        snapshot=copy.deepcopy(value);published.validate_api(value,'Debug-automatic');self.assertEqual(snapshot,value)
        with self.assertRaises(ValueError):published.validate_api(record,'Release-sse2')

    def members(self,profile):
        values={'hosted-native-class-interactions/'+profile+'/collection.json':b'original bytes',
                'hosted-native-class-interactions/'+profile+'/original-population.csv':b'original bytes'}
        for name in published.load(published.original.LOCK)['selected_plans']:
            stem=Path(name).stem;values['native-class-interactions/'+profile+'/'+stem+'/interactions.json']=b'original bytes'
            values['hosted-native-class-interactions/'+profile+'/'+stem+'-audit.json']=b'original bytes'
        values['native-class-interactions/'+profile+'/scope/assets/a.bin']=b'shared exact asset'*2048
        values['native-class-interactions/'+profile+'/scope/assets/b.bin']=b'shared exact asset'*2048
        return values

    def test_every_logical_original_member_is_retained_while_identical_bytes_share_disk_space(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);archive=base/'input.zip';profile='Debug-automatic';expected=self.members(profile)
            with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as incoming:
                for name,body in expected.items():incoming.writestr(name,body)
            files,materialized,storage=published.restore_archive(archive,base/'payload',profile,base/'owner')
            self.assertEqual(set(files),set(expected));self.assertEqual(storage['unique_file_contents'],2)
            self.assertLess(storage['unique_materialized_bytes'],storage['complete_logical_bytes']);self.assertTrue(storage['all_logical_members_retained'])
            a=base/'payload'/('native-class-interactions/'+profile+'/scope/assets/a.bin');b=a.with_name('b.bin')
            self.assertEqual(a.stat().st_ino,b.stat().st_ino)
            for name,body in expected.items():self.assertEqual((base/'payload'/name).read_bytes(),body)
            self.assertEqual(len(materialized),len(expected))
            a.write_bytes(b'changed shared asset')
            with self.assertRaises(ValueError):published.verify_members(base/'payload',files)

    def test_replaced_canonical_alias_cannot_escape_complete_member_verification(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);archive=base/'input.zip';profile='Debug-automatic';expected=self.members(profile)
            with zipfile.ZipFile(archive,'w') as incoming:
                for name,body in expected.items():incoming.writestr(name,body)
            files,materialized,_=published.restore_archive(archive,base/'payload',profile,base/'owner')
            selected=next(p for p in materialized if '/assets/' in p);path=Path(selected);path.unlink();path.write_bytes(b'replaced')
            canonical={Path(p).relative_to(base/'owner/out').as_posix():v for p,v in materialized.items()}
            with self.assertRaises(ValueError):published.verify_members(base/'owner/out',canonical)
            published.verify_members(base/'payload',files)

    def test_missing_original_scope_redirect_traversal_and_privileged_members_are_rejected(self):
        for kind in ('missing','traversal','symlink','privileged','case-alias'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                base=Path(temp);archive=base/'input.zip';profile='Debug-automatic';expected=self.members(profile)
                if kind=='missing':expected.pop(next(n for n in expected if n.endswith('-audit.json')))
                with zipfile.ZipFile(archive,'w') as incoming:
                    for name,body in expected.items():incoming.writestr(name,body)
                    if kind=='traversal':incoming.writestr('../outside',b'bad')
                    elif kind=='case-alias':incoming.writestr(next(iter(expected)).upper(),b'bad')
                    elif kind in ('symlink','privileged'):
                        info=zipfile.ZipInfo('unsafe');info.create_system=3;info.external_attr=((stat.S_IFLNK|0o777) if kind=='symlink' else (stat.S_IFREG|0o4755))<<16;incoming.writestr(info,b'bad')
                with self.assertRaises(ValueError):published.restore_archive(archive,base/'payload',profile,base/'owner')
                self.assertFalse((base/'outside').exists())

    def test_standalone_download_and_replay_help_require_no_simulator_or_large_inputs(self):
        for name in ('download_published_class_interactions.py','inspect_published_class_interactions.py'):
            result=subprocess.run([sys.executable,'-B',str(ROOT/'Tests/Production/Closeout'/name),'--help'],cwd=ROOT,
                                  stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr);self.assertIn('--profile',result.stdout)
