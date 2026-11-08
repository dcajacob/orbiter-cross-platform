"""Reference reuse cannot accept an incomplete audit, an old cohort or altered ZIP members."""
import copy
from pathlib import Path
import stat
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile
from contracts import ROOT
sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
import restore_reference as reader


class HostedOriginalReferenceRestoreTests(unittest.TestCase):
    def api(self):
        return dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),
            run=dict(id=1,repository=dict(full_name='dcajacob/orbiter-cross-platform'),head_sha=reader.AUDITOR,
                     head_branch='qualification/original-stock-audit-v1',path='.github/workflows/phase6-original-stock-audit.yml',
                     run_attempt=1,status='completed',conclusion='success'),
            artifact=dict(id=2,name='original-stock-independent-audit',expired=False,size_in_bytes=100,
                          digest='sha256:'+'a'*64,workflow_run=dict(id=1,head_sha=reader.AUDITOR)),
            jobs=[dict(name='audit',run_id=1,head_sha=reader.AUDITOR,status='completed',conclusion='success',labels=['ubuntu-24.04'],
                       steps=[dict(name=name,status='completed',conclusion='success') for name in reader.STEPS])])

    def test_only_the_actual_complete_independent_audit_can_supply_a_reference(self):
        self.assertEqual(reader.validate_audit_api(self.api())['name'],'audit')
        for change in (lambda r:r['run'].update(head_sha='f'*40),lambda r:r['run'].update(conclusion='failure'),
                       lambda r:r['run'].update(status='in_progress'),lambda r:r['run'].update(run_attempt=2),
                       lambda r:r['run']['repository'].update(full_name='another/repository'),
                       lambda r:r['artifact'].update(expired=True),lambda r:r['artifact']['workflow_run'].update(id=3),
                       lambda r:r['jobs'][0].update(labels=['self-hosted']),
                       lambda r:r['jobs'][0]['steps'][0].update(conclusion='skipped'),lambda r:r['jobs'].append(copy.deepcopy(r['jobs'][0]))):
            record=self.api();change(record)
            with self.assertRaises(ValueError):reader.validate_audit_api(record)

    def receipts(self):
        transport=dict(status='passed',protocol=reader.transport.PROTOCOL,source_commit=reader.ORIGINAL,phase6_complete=False,native_admission_qualified=False)
        writer=dict(status='passed',producer_commit=reader.ORIGINAL,protocol='remaining-stock-matched-clock-v2',download_manifest_sha256='a'*64,
                    processes=304,presentations=304*960,profiles={p:{} for p in reader.PROFILES},phase6_complete=False,native_admission_qualified=False)
        cohort=dict(protocol='phase6-hosted-original-windows-persistence-audit-v1',status='passed-original-Windows-writer-and-exact-save-reload-audit',
                    observer_source=reader.ORIGINAL,auditor_source=reader.AUDITOR,transport_sha256='a'*64,writer_audit_sha256='b'*64,
                    actual_windows_processes=608,actual_windows_presentations=608*960,writer_processes=304,reload_processes=304,
                    profiles={p:{} for p in reader.PROFILES},build_pairs=dict(automatic={},sse2={}),phase6_complete=False,native_admission_qualified=False)
        return transport,writer,cohort

    def test_both_complete_phases_and_every_original_profile_are_required(self):
        reader.audit_receipts(*self.receipts(),'a'*64,'b'*64)
        for change in (lambda t,w,c:w.update(processes=303),lambda t,w,c:c.update(actual_windows_processes=607),
                       lambda t,w,c:c.update(reload_processes=0),lambda t,w,c:c.update(build_pairs={'automatic':{}}),
                       lambda t,w,c:c.update(observer_source='fc3a3a300c60fd2386b28662839b24df084fad7f'),
                       lambda t,w,c:w.update(download_manifest_sha256='c'*64),lambda t,w,c:c.update(writer_audit_sha256='d'*64),
                       lambda t,w,c:c.update(phase6_complete=True),lambda t,w,c:t.update(native_admission_qualified=True)):
            values=self.receipts();change(*values)
            with self.assertRaises(ValueError):reader.audit_receipts(*values,'a'*64,'b'*64)

    def test_decoding_is_read_only_and_rejects_aliases_links_and_escapes(self):
        for names in (('folder/evidence.json',),('../escape',),('C:/escape',),('folder/a','folder/A'),('symlink',)):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);archive=root/'source.zip'
                with zipfile.ZipFile(archive,'w') as z:
                    for name in names:
                        if name=='symlink':
                            info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,'../escape')
                        else:z.writestr(name,b'original evidence bytes')
                original=reader.sha(archive)
                with patch.object(reader.shutil,'disk_usage',return_value=types.SimpleNamespace(free=32*1024**3)):
                    if names==('folder/evidence.json',):
                        reader.extract(archive,root/'decoded');self.assertEqual((root/'decoded/folder/evidence.json').read_bytes(),b'original evidence bytes')
                    else:
                        with self.assertRaises(ValueError):reader.extract(archive,root/'decoded')
                self.assertEqual(reader.sha(archive),original);self.assertFalse((root/'escape').exists())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);archive=root/'source.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('evidence',b'original')
            with patch.object(reader.shutil,'disk_usage',return_value=types.SimpleNamespace(free=8*1024**3-1)):
                with self.assertRaises(ValueError):reader.extract(archive,root/'decoded')


if __name__=='__main__':unittest.main()
