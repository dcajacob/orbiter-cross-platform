"""Publication replay controls preserve all captured source/metadata identities without new runtime credit."""
import copy
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import subprocess
import sys
import warnings
import unittest
from unittest.mock import patch
import zipfile
from contracts import ROOT
import inspect_published_class_capabilities as published


class PublishedClassCapabilitiesTests(unittest.TestCase):
    def fixture(self):return json.loads((ROOT/'Tests/Production/Closeout/published-class-capability-api.fixture.json').read_text())

    def test_complete_original_source_roster_and_exact_published_profile_bytes_are_required(self):
        record=self.fixture();before=copy.deepcopy(record);lock,pin=published.validate_api(record,'Debug-sse2')
        self.assertEqual(record,before);self.assertEqual(pin['artifact_id'],13735853739);self.assertEqual(len(lock['profiles']),4)
        for mutate in (lambda r:r['run'].update(head_sha='e'*40),lambda r:r['jobs'].pop(),
                       lambda r:r['jobs'][0].update(labels=['self-hosted']),lambda r:r['jobs'][0].update(conclusion='failure'),
                       lambda r:r['artifact'].update(digest='sha256:'+'0'*64),lambda r:r['artifact'].update(expired=True)):
            value=self.fixture();mutate(value)
            with self.assertRaises(ValueError):published.validate_api(value,'Debug-sse2')

    def test_all_original_archive_members_are_retained_without_link_escape_or_overwrite(self):
        profile='Debug-sse2';names=['native-class-capabilities/'+profile+'/'+n for n in ('capabilities.json','capability-probe.so','observer-build-command.json')]
        names+=['hosted-native-class-capabilities/'+profile+'/'+n for n in ('collection.json','original-capabilities-audit.json')]
        for damage in (None,'duplicate','symlink','overwrite'):
            with self.subTest(damage=damage),tempfile.TemporaryDirectory() as temp:
                base=Path(temp);owner=base/'owner';owner.mkdir();archive=base/'published.zip'
                with zipfile.ZipFile(archive,'w') as out,warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    for name in names:out.writestr(name,b'original')
                    out.writestr('reference-api/original.json',b'original receipt')
                    if damage=='duplicate':out.writestr(names[0],b'changed')
                    if damage=='symlink':
                        entry=zipfile.ZipInfo('link');entry.create_system=3;entry.external_attr=(stat.S_IFLNK|0o777)<<16;out.writestr(entry,b'/tmp/outside')
                if damage=='overwrite':
                    target=owner/'out'/names[0];target.parent.mkdir(parents=True);target.write_bytes(b'keep')
                if damage:
                    with self.assertRaises(ValueError):published.restore_archive(archive,base/'payload',profile,owner)
                    if damage=='overwrite':self.assertEqual(target.read_bytes(),b'keep')
                else:
                    files,materialized=published.restore_archive(archive,base/'payload',profile,owner)
                    self.assertEqual(len(files),6);self.assertEqual(len(materialized),5)
                    self.assertEqual((base/'payload/reference-api/original.json').read_bytes(),b'original receipt')

    def test_old_receipt_bytes_and_fresh_receipts_remain_separate_without_runtime_guard_substitution(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);owner=base/'owner';payload=base/'payload';owner.mkdir();payload.mkdir()
            current=owner/'out/reference-api/original.json';old=payload/'reference-api/original.json'
            current.parent.mkdir(parents=True);old.parent.mkdir(parents=True);current.write_bytes(b'new receipt');old.write_bytes(b'old receipt')
            runtime=owner/'out/runtime/observer.so';runtime.parent.mkdir(parents=True);runtime.write_bytes(b'original runtime')
            fake=payload/'runtime/observer.so';fake.parent.mkdir(parents=True);fake.write_bytes(b'original runtime')
            values={str(current):hashlib.sha256(b'old receipt').hexdigest(),str(runtime):hashlib.sha256(b'original runtime').hexdigest()};before=copy.deepcopy(values)
            resolved=published.old_guarded_inputs(values,payload,owner);self.assertEqual(values,before)
            self.assertEqual(resolved[str(current)]['path'],str(old));self.assertEqual(resolved[str(runtime)]['path'],str(runtime))
            self.assertEqual(current.read_bytes(),b'new receipt');self.assertEqual(old.read_bytes(),b'old receipt')
            runtime.write_bytes(b'changed')
            with self.assertRaises(ValueError):published.old_guarded_inputs(values,payload,owner)
            runtime.write_bytes(b'original runtime');old.write_bytes(b'changed receipt')
            with self.assertRaises(ValueError):published.old_guarded_inputs(values,payload,owner)
            with self.assertRaises(ValueError):published.old_guarded_inputs({'/tmp/outside':hashlib.sha256(b'x').hexdigest()},payload,owner)


    def test_byte_identical_replay_preserves_original_metadata_locations_in_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);capture=base/'capture.json';old=base/'published-audit.json';new=base/'replayed-audit.json'
            old.write_bytes(b'original complete audit');new.write_bytes(old.read_bytes())
            with patch.object(published.original,'inspect_profile',return_value={'original':'scope'}) as inspect:
                result=published.reproduce_scope('Debug-sse2',capture,old,new)
                inspect.assert_called_once_with('Debug-sse2',capture,old);self.assertEqual(result,{'original':'scope'})
            new.write_bytes(b'changed audit')
            with patch.object(published.original,'inspect_profile') as inspect:
                with self.assertRaises(ValueError):published.reproduce_scope('Debug-sse2',capture,old,new)
                inspect.assert_not_called()


    def test_standalone_auditor_help_has_complete_import_paths_without_runtime(self):
        result=subprocess.run([sys.executable,'-B',str(ROOT/'Tests/Production/Closeout/inspect_published_class_capabilities.py'),'--help'],
                              cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('--archive',result.stdout);self.assertIn('--profile',result.stdout)
