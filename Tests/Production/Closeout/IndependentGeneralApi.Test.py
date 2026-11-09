"""Raw native API proof restoration must keep exact provenance and all original bytes."""
import ast
import copy
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
import warnings
import zipfile
from contracts import ROOT
import inspect_hosted_native_general_api as reader


class IndependentGeneralApiTests(unittest.TestCase):
    def test_actual_api_and_all_profiles_require_exact_closed_jobs_and_artifacts(self):
        fixture=json.loads((ROOT/'Tests/Production/Closeout/native-api-published-source.fixture.json').read_text())
        self.assertFalse(fixture['qualification_granted'])
        record=fixture['record']
        self.assertEqual(reader.validate_api(record,'Debug-automatic')['id'],129448961099)
        for mutate in (lambda r:r['run'].update(run_attempt=2),lambda r:r['run'].update(status='in_progress'),
                       lambda r:r['run'].update(head_sha='f'*40),lambda r:r['artifact'].update(id=1),
                       lambda r:r['artifact'].update(size_in_bytes=1),lambda r:r['artifact'].update(digest='sha256:'+'f'*64),
                       lambda r:r['artifact'].update(expired=True),lambda r:r['jobs'].pop(),
                       lambda r:r['jobs'][1].update(conclusion='skipped'),
                       lambda r:r['jobs'][1].update(labels=['ubuntu-24.04','self-hosted'])):
            changed=copy.deepcopy(record);mutate(changed)
            with self.assertRaises(ValueError):reader.validate_api(changed,'Debug-automatic')

    def test_complete_raw_restore_preserves_every_byte_and_original_member_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);archive=root/'raw.zip';owner=root/'owner';owner.mkdir();profile='Debug-automatic'
            members={'native-general-api-capture/'+profile+'/diagnostic.json':b'{"fixture":true}\n',
                     **{'native-stock-assets/'+n:b'original-'+n.encode() for n in ('remaining-vessels-resources.json','resources.json','cockpit-test-font.json')},
                     'hosted-native-api/'+profile+'/collection.json':b'original collection fixture'}
            with zipfile.ZipFile(archive,'w') as incoming:
                for name,body in members.items():incoming.writestr(name,body)
            files,materialized=reader.restore_archive(archive,root/'retained',profile,owner)
            self.assertEqual(set(files),set(members));self.assertEqual(len(materialized),4)
            for name,body in members.items():
                self.assertEqual((root/'retained'/name).read_bytes(),body)
                self.assertEqual(files[name],dict(sha256=reader.hashlib.sha256(body).hexdigest(),bytes=len(body)))
            for path,checksum in materialized.items():self.assertEqual(reader.sha(path),checksum)
            self.assertFalse((owner/'out/hosted-native-api').exists())

    def test_unsafe_duplicate_symlink_and_existing_raw_outputs_cannot_be_restored(self):
        for damage in ('escape','duplicate','symlink','overwrite'):
            with self.subTest(damage=damage),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);archive=root/'raw.zip';owner=root/'owner';owner.mkdir();profile='Debug-automatic'
                name='native-general-api-capture/'+profile+'/diagnostic.json'
                with zipfile.ZipFile(archive,'w') as incoming,warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    if damage=='escape':incoming.writestr('../escape',b'bad')
                    elif damage=='symlink':
                        info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;incoming.writestr(info,b'/tmp/escape')
                    else:
                        incoming.writestr(name,b'original')
                        if damage=='duplicate':incoming.writestr(name,b'other')
                if damage=='overwrite':
                    old=owner/'out'/name;old.parent.mkdir(parents=True);old.write_bytes(b'keep-existing')
                with self.assertRaises(ValueError):reader.restore_archive(archive,root/'retained',profile,owner)
                if damage=='overwrite':self.assertEqual(old.read_bytes(),b'keep-existing')
                self.assertFalse((root/'escape').exists())

    def test_independent_route_keeps_original_auditor_and_all_scope_boundaries(self):
        original='Tests/Production/GeneralApiCorrection/audit_native.py'
        self.assertEqual((ROOT/original).read_bytes(),subprocess.check_output(['git','-C',str(ROOT),'show',reader.SOURCE+':'+original]))
        for name in ('inspect_hosted_native_general_api.py','final_hosted_native_general_api.py'):
            ast.parse((ROOT/'Tests/Production/Closeout'/name).read_bytes())
        workflow=(ROOT/'.github/workflows/phase6-native-general-api-independent.yml').read_text()
        self.assertEqual(workflow.count('runs-on: ubuntu-24.04'),3)
        self.assertIn('max-parallel: 2',workflow);self.assertIn('cancel-in-progress: false',workflow)
        self.assertIn('inspect_hosted_native_general_api.py',workflow)
        self.assertNotIn('capture_native.py',workflow);self.assertNotIn('continue-on-error',workflow)
        source=(ROOT/'Tests/Production/Closeout/inspect_hosted_native_general_api.py').read_text()
        self.assertIn('output.read_bytes()==old_audit.read_bytes()',source)
        self.assertIn('all(sha(path)==value for path,value in original_audit',source)
        self.assertIn('complete_general_api_qualification=False',source)


if __name__=='__main__':unittest.main()
