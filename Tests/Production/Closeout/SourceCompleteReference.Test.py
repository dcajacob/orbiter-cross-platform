"""A fresh reference cannot inherit the rejected old cohort or bypass the full independent audit."""
import ast
import copy
from pathlib import Path
import sys
import unittest
from contracts import ROOT
sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
import restore_source_complete_reference as reader


class SourceCompleteReferenceTests(unittest.TestCase):
    def api(self):
        return dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),
            run=dict(id=1,repository=dict(full_name='dcajacob/orbiter-cross-platform'),head_sha=reader.AUDITOR,
                head_branch='qualification/original-source-audit-v2',path='.github/workflows/phase6-original-source-audit.yml',
                run_attempt=1,status='completed',conclusion='success'),
            artifact=dict(id=2,name='source-complete-original-stock-independent-audit',expired=False,size_in_bytes=100,
                digest='sha256:'+'a'*64,workflow_run=dict(id=1,head_sha=reader.AUDITOR)),
            jobs=[dict(name='audit',run_id=1,head_sha=reader.AUDITOR,status='completed',conclusion='success',labels=['ubuntu-24.04'],
                steps=[dict(name=name,status='completed',conclusion='success') for name in reader.STEPS])])

    def receipts(self):
        manifest=dict(status='passed',protocol=reader.transport.PROTOCOL,source_commit=reader.ORIGINAL,phase6_complete=False,native_admission_qualified=False)
        writer=dict(status='passed',producer_commit=reader.ORIGINAL,protocol='remaining-stock-matched-clock-v2',download_manifest_sha256='a'*64,
            processes=304,presentations=304*960,profiles={p:{} for p in reader.PROFILES},phase6_complete=False,native_admission_qualified=False)
        cohort=dict(protocol='phase6-source-complete-original-windows-persistence-audit-v2',
            status='passed-source-complete-original-Windows-writer-and-exact-save-reload-audit',
            observer_source=reader.ORIGINAL,auditor_source=reader.AUDITOR,transport_sha256='a'*64,writer_audit_sha256='b'*64,
            actual_windows_processes=608,actual_windows_presentations=608*960,writer_processes=304,reload_processes=304,
            profiles={p:{} for p in reader.PROFILES},build_pairs=dict(automatic={},sse2={}),phase6_complete=False,native_admission_qualified=False)
        return manifest,writer,cohort

    def test_old_failed_incomplete_or_wrong_namespace_audit_never_supplies_a_reference(self):
        self.assertEqual(reader.validate_audit_api(self.api())['name'],'audit')
        for change in (lambda r:r['run'].update(head_sha='9af22bbd320b54025e9345f6bfbd05260d2287e8'),
                       lambda r:r['run'].update(head_branch='qualification/original-stock-audit-v1'),
                       lambda r:r['run'].update(path='.github/workflows/phase6-original-stock-audit.yml'),
                       lambda r:r['run'].update(conclusion='failure'),lambda r:r['run'].update(status='in_progress'),
                       lambda r:r['run'].update(run_attempt=2),lambda r:r['artifact'].update(name='original-stock-independent-audit'),
                       lambda r:r['artifact'].update(expired=True),lambda r:r['artifact']['workflow_run'].update(id=3),
                       lambda r:r['artifact']['workflow_run'].update(head_sha='f'*40),lambda r:r['jobs'][0].update(labels=['self-hosted']),
                       lambda r:r['jobs'][0]['steps'][0].update(conclusion='skipped'),
                       lambda r:r['jobs'][0]['steps'][1].update(conclusion='skipped'),lambda r:r['jobs'].append(copy.deepcopy(r['jobs'][0]))):
            record=self.api();change(record)
            with self.assertRaises(ValueError):reader.validate_audit_api(record)

    def test_all_608_actual_processes_and_both_build_pairs_keep_their_original_identities(self):
        reader.audit_receipts(*self.receipts(),'a'*64,'b'*64)
        for change in (lambda m,w,c:m.update(protocol='remaining-stock-hosted-transport-v1'),
                       lambda m,w,c:m.update(source_commit='f9bf6c7814965cd897f349f97890d9e005cbb66d'),
                       lambda m,w,c:w.update(processes=303),lambda m,w,c:c.update(actual_windows_processes=607),
                       lambda m,w,c:c.update(reload_processes=0),lambda m,w,c:c.update(build_pairs=dict(automatic={})),
                       lambda m,w,c:c.update(protocol='phase6-hosted-original-windows-persistence-audit-v1'),
                       lambda m,w,c:c.update(auditor_source='9af22bbd320b54025e9345f6bfbd05260d2287e8'),
                       lambda m,w,c:c.update(writer_audit_sha256='c'*64),lambda m,w,c:c.update(phase6_complete=True),
                       lambda m,w,c:m.update(native_admission_qualified=True)):
            values=self.receipts();change(*values)
            with self.assertRaises(ValueError):reader.audit_receipts(*values,'a'*64,'b'*64)

    def test_fresh_reference_api_archive_digests_must_equal_every_independently_audited_artifact(self):
        run=dict(id=reader.transport.RUN,head_sha=reader.ORIGINAL,head_branch=reader.transport.BRANCH)
        artifacts=[dict(id=index+1,name='matched-clock-remaining-stock-v2-'+profile,size_in_bytes=100,
            digest='sha256:'+'a'*64,expired=False,workflow_run=run) for index,profile in enumerate(sorted(reader.PROFILES))]
        recorded=dict(artifacts=artifacts);fresh=copy.deepcopy(recorded)
        manifest=dict(workflow_run=run,artifacts=[dict(api_artifact=item) for item in copy.deepcopy(artifacts)])
        self.assertEqual(set(reader.bind_artifacts(recorded,fresh,manifest)),reader.PROFILES)
        for change in (lambda r:r['artifacts'][0].update(id=99),lambda r:r['artifacts'][0].update(digest='sha256:'+'b'*64),
                       lambda r:r['artifacts'][0].update(size_in_bytes=101),lambda r:r['artifacts'][0]['workflow_run'].update(head_sha='f'*40),
                       lambda r:r['artifacts'].pop()):
            changed=copy.deepcopy(fresh);change(changed)
            with self.assertRaises(ValueError):reader.bind_artifacts(recorded,changed,manifest)

    def test_old_restoration_body_safety_and_evidence_guards_are_conserved(self):
        old=(ROOT/'Tests/Production/CurrentWindows/Hosted/restore_reference.py').read_text()
        new=Path(reader.__file__).read_text()
        def body(source,name):return ast.dump(next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name),include_attributes=False)
        for name in ('bind_artifacts','extract'):self.assertEqual(body(old,name),body(new,name))
        changes=[
            ('import source_complete_original_transport as transport','import hosted_transport as transport'),
            ('from audit_source_complete_original_stock import PRODUCER as ORIGINAL,PROFILES,writer_result','from audit_hosted_original_stock import PRODUCER as ORIGINAL,PROFILES,writer_result'),
            (reader.AUDITOR,'9af22bbd320b54025e9345f6bfbd05260d2287e8'),
            ('qualification/original-source-audit-v2','qualification/original-stock-audit-v1'),
            ('.github/workflows/phase6-original-source-audit.yml','.github/workflows/phase6-original-stock-audit.yml'),
            ('source-complete-original-stock-independent-audit','original-stock-independent-audit'),
            ('phase6-source-complete-original-windows-persistence-audit-v2','phase6-hosted-original-windows-persistence-audit-v1'),
            ('passed-source-complete-original-Windows-writer-and-exact-save-reload-audit','passed-original-Windows-writer-and-exact-save-reload-audit'),
            ("fresh['workflow_run']['id']==transport.RUN","fresh['workflow_run']['id']==42515116858"),
            ('phase6-source-complete-original-reference-restoration-v2','phase6-audited-original-reference-restoration-v1')]
        for before,after in changes:self.assertEqual(new.count(before),1);new=new.replace(before,after,1)
        for name in ('validate_audit_api','audit_receipts','main'):self.assertEqual(body(old,name),body(new,name))
        self.assertIn('source_complete_original_transport as transport',Path(reader.__file__).read_text())
        self.assertIn('unchanged reserve required',Path(reader.__file__).read_text())


if __name__=='__main__':unittest.main()
