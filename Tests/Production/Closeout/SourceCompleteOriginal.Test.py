"""Fresh original API identities and all original archive/physics guards remain strict."""
import ast
import copy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from contracts import ROOT
import source_complete_original_transport as transport


class SourceCompleteOriginalTests(unittest.TestCase):
    def record(self):
        run=dict(id=transport.RUN,head_sha=transport.SOURCE,head_branch=transport.BRANCH,path=transport.WORKFLOW,
            run_attempt=1,status='completed',conclusion='success',repository=dict(full_name=transport.legacy.REPOSITORY))
        url=f'https://api.github.com/repos/{transport.legacy.REPOSITORY}/actions/runs/{transport.RUN}'
        jobs=[]
        for n,profile in enumerate(sorted(transport.legacy.PROFILES)):
            steps=[dict(name=name,status='completed',conclusion='success') for name in transport.STEPS]
            steps.append(dict(name='Select original SSE2 CRT when required',status='completed',conclusion='success' if profile.endswith('-sse2') else 'skipped'))
            jobs.append(dict(id=1000+n,run_id=transport.RUN,head_sha=transport.SOURCE,head_branch=transport.BRANCH,run_url=url,
                name=transport.JOB_PREFIX+profile.replace('-',' '),status='completed',conclusion='success',labels=['windows-2025'],steps=steps))
        steps=[dict(name=name,status='completed',conclusion='success') for name in (
            'Verify recursive source collection and every unchanged helper control',
            'Bind original rejected captures and partial independent audit to their actual API bytes',
            'Independently identify every missing recorded source without modifying old capture metadata','Run actions/upload-artifact@v7')]
        jobs.append(dict(id=128926685702,run_id=transport.RUN,head_sha=transport.SOURCE,head_branch=transport.BRANCH,run_url=url,
            name='provenance',status='completed',conclusion='success',labels=['ubuntu-24.04'],steps=steps))
        return run,jobs

    def test_exact_complete_source_cohort_cannot_be_replaced_with_old_or_partial_results(self):
        run,jobs=self.record();actual=transport.run_identity(run,jobs)
        self.assertEqual(transport.run_identity(actual),actual)
        for change in (lambda r,j:r.update(head_sha='f9bf6c7814965cd897f349f97890d9e005cbb66d'),
                       lambda r,j:r.update(conclusion='failure'),lambda r,j:r.update(run_attempt=2),
                       lambda r,j:j.pop(),lambda r,j:j[-1]['steps'][0].update(conclusion='skipped'),
                       lambda r,j:j[0]['steps'][0].update(conclusion='skipped'),lambda r,j:j[0].update(labels=['self-hosted']),
                       lambda r,j:j[0].update(head_sha='f'*40)):
            r=copy.deepcopy(run);j=copy.deepcopy(jobs);change(r,j)
            with self.assertRaises(ValueError):transport.run_identity(r,j)

    def test_actual_four_archive_closure_and_mutated_raw_member_are_checked(self):
        saved=transport.ROOT
        try:
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);transport.ROOT=root;archives=root/'out/archives';archives.mkdir(parents=True)
                run,jobs=self.record();artifacts=[]
                for n,profile in enumerate(sorted(transport.legacy.PROFILES)):
                    name='matched-clock-remaining-stock-v2-'+profile;path=archives/(name+'.zip')
                    with zipfile.ZipFile(path,'w') as archive:archive.writestr('receipt.json',json.dumps(dict(fixture_only=True,profile=profile)))
                    artifacts.append(dict(id=2000+n,name=name,size_in_bytes=path.stat().st_size,digest='sha256:'+transport.sha(path),expired=False,
                        workflow_run=dict(id=transport.RUN,head_sha=transport.SOURCE,head_branch=transport.BRANCH)))
                manifest=transport.retain(dict(workflow_run=run,jobs=jobs,artifacts=artifacts),archives,root/'out/decoded')
                decoded={profile:root/'out/decoded'/profile for profile in transport.legacy.PROFILES}
                self.assertEqual(set(transport.inspect_matrix(manifest,root,decoded,transport.SOURCE)),transport.legacy.PROFILES)
                self.assertFalse(manifest['phase6_complete']);self.assertFalse(manifest['native_admission_qualified'])
                (next(iter(decoded.values()))/'receipt.json').write_text('damaged actual member')
                with self.assertRaises(ValueError):transport.inspect_matrix(manifest,root,decoded,transport.SOURCE)
        finally:transport.ROOT=saved

    def test_archive_and_full_physical_audit_bodies_are_conserved(self):
        original=(ROOT/'Tests/Production/RemainingStockPersistence/hosted_transport.py').read_text();current=Path(transport.__file__).read_text()
        def body(source,name):return ast.dump(next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name),include_attributes=False)
        for name in ('inspect_matrix','retain'):self.assertEqual(body(original,name),body(current,name))
        new=(ROOT/'Tests/Production/Closeout/audit_source_complete_original_stock.py').read_text()
        changes=[("PRODUCER='ba38a7efccb5f770e87add95f5e966aa40270756'","PRODUCER='f9bf6c7814965cd897f349f97890d9e005cbb66d'"),
            ('        import source_complete_original_transport as hosted_transport\n','        import hosted_transport\n'),
            ("protocol='phase6-source-complete-original-windows-persistence-audit-v2'","protocol='phase6-hosted-original-windows-persistence-audit-v1'"),
            ("status='passed-source-complete-original-Windows-writer-and-exact-save-reload-audit'","status='passed-original-Windows-writer-and-exact-save-reload-audit'")]
        for before,after in changes:self.assertEqual(new.count(before),1);new=new.replace(before,after,1)
        self.assertEqual(new,(ROOT/'Tests/Production/Closeout/audit_hosted_original_stock.py').read_text())


if __name__=='__main__':unittest.main()
