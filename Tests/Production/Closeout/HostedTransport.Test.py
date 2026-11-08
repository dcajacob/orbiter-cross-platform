"""Reject mixed, incomplete or damaged hosted stock evidence; fixtures are not flights."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
import zipfile

from contracts import ROOT


class HostedTransportTests(unittest.TestCase):
    def setUp(self):
        self.path=list(sys.path)
        self.saved={n:sys.modules.pop(n,None) for n in ('transport','observations','hosted_transport')}
        sys.path.insert(0,str(ROOT/'Tests/Production/RemainingStockPersistence'))
        self.hosted=importlib.import_module('hosted_transport')
        self.legacy=importlib.import_module('transport')

    def tearDown(self):
        sys.path[:]=self.path
        for n,original in self.saved.items():
            sys.modules.pop(n,None)
            if original is not None:sys.modules[n]=original

    def records(self):
        run=dict(id=123,head_sha='a'*40,head_branch='codex/github-qualification',
            path='.github/workflows/phase6-qualification.yml',status='completed',conclusion='failure',
            repository={'full_name':'dcajacob/orbiter-cross-platform'})
        jobs=[]
        for index,profile in enumerate(sorted(self.legacy.PROFILES)):
            steps=[dict(name=n,status='completed',conclusion='success') for n in self.hosted.STEPS]
            steps.append(dict(name='Select original SSE2 CRT when required',status='completed',
                conclusion='success' if profile.endswith('-sse2') else 'skipped'))
            jobs.append(dict(id=1000+index,run_id=123,head_sha=run['head_sha'],head_branch=run['head_branch'],
                run_url='https://api.github.com/repos/dcajacob/orbiter-cross-platform/actions/runs/123',
                name=self.hosted.JOB_PREFIX+profile.replace('-',' '),status='completed',conclusion='success',steps=steps))
        return run,jobs

    def test_stock_cohort_accepts_overall_native_failure_and_retains_it(self):
        run,jobs=self.records();value=self.hosted.run_identity(run,jobs)
        self.assertEqual(value['conclusion'],'failure')
        self.assertEqual(len(value['stock_jobs']),4)
        self.assertEqual(self.hosted.run_identity(value),value)

    def test_workflow_repository_branch_completion_and_source_are_closed(self):
        run,jobs=self.records()
        for key,value in [('id',True),('id',0),('head_sha','bad'),('head_branch','main'),
                          ('path','.github/workflows/matched-clock-remaining-stock-full.yml'),
                          ('status','in_progress'),('conclusion','cancelled'),
                          ('repository',{'full_name':'someone/else'})]:
            changed=copy.deepcopy(run);changed[key]=value
            with self.subTest(key=key,value=value),self.assertRaises((ValueError,KeyError)):
                self.hosted.run_identity(changed,jobs)

    def test_each_stock_job_must_succeed_with_exact_run_source_and_profile(self):
        run,jobs=self.records()
        for key,value in [('id',True),('run_id',124),('head_sha','b'*40),('head_branch','main'),
                          ('run_url','https://api.github.com/repos/other/repo/actions/runs/123'),
                          ('name','Other successful job'),('status','queued'),('conclusion','failure'),('conclusion','skipped')]:
            changed=copy.deepcopy(jobs);changed[0][key]=value
            with self.subTest(key=key),self.assertRaises((ValueError,KeyError)):
                self.hosted.run_identity(run,changed)
        for changed in (jobs[:-1],jobs+[jobs[0]],jobs[:3]+[jobs[0]]):
            with self.assertRaises(ValueError):self.hosted.run_identity(run,changed)

    def test_required_capture_controls_reload_and_upload_cannot_be_skipped(self):
        run,jobs=self.records()
        for index in range(len(self.hosted.STEPS)):
            for mutation in ('missing','duplicate','failure','skipped'):
                changed=copy.deepcopy(jobs);steps=changed[0]['steps']
                if mutation=='missing':steps.pop(index)
                elif mutation=='duplicate':steps.append(copy.deepcopy(steps[index]))
                else:steps[index]['conclusion']=mutation
                with self.subTest(index=index,mutation=mutation),self.assertRaises(ValueError):
                    self.hosted.run_identity(run,changed)

    def test_math_lane_and_step_contract_matches_the_actual_reused_workflow(self):
        run,jobs=self.records()
        for index in range(4):
            changed=copy.deepcopy(jobs);step=changed[index]['steps'][-1]
            step['conclusion']='success' if step['conclusion']=='skipped' else 'skipped'
            with self.assertRaises(ValueError):self.hosted.run_identity(run,changed)
        source=(ROOT/'.github/workflows/matched-clock-remaining-stock-full.yml').read_text()
        names=re.findall(r'^\s*- name: (.+)$',source,re.M)
        self.assertTrue(set(self.hosted.STEPS)-{'Run actions/upload-artifact@v7'}<=set(names))
        self.assertIn('uses: actions/upload-artifact@v7',source)

    def test_legacy_run_identity_remains_strict(self):
        run,jobs=self.records()
        with self.assertRaises(ValueError):self.legacy.run_identity(run,False)
        run.update(head_branch='codex/production-bootstrap',path=self.legacy.WORKFLOWS[False],conclusion='success')
        self.assertEqual(self.legacy.run_identity(run,False)['head_sha'],'a'*40)

    def fixture_archives(self,root,member='identity.json'):
        run,jobs=self.records();artifacts=[]
        for index,profile in enumerate(sorted(self.legacy.PROFILES)):
            name='matched-clock-remaining-stock-v2-'+profile;p=root/(name+'.zip')
            with zipfile.ZipFile(p,'w') as z:z.writestr(member,json.dumps({'profile':profile,'fixture_only':True}))
            artifacts.append(dict(id=2000+index,name=name,size_in_bytes=p.stat().st_size,
                digest='sha256:'+hashlib.sha256(p.read_bytes()).hexdigest(),expired=False,
                workflow_run={k:run[k] for k in ('id','head_sha','head_branch')}))
        return dict(workflow_run=run,jobs=jobs,artifacts=artifacts)

    def test_local_bytes_decode_dispatch_and_incomplete_acceptance_scope(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'out') as tmp:
            root=Path(tmp);records=self.fixture_archives(root)
            manifest=self.hosted.retain(records,root,root/'decoded')
            self.assertFalse(manifest['phase6_complete']);self.assertFalse(manifest['native_admission_qualified'])
            decoded={i['profile']:ROOT/i['decoded'] for i in manifest['artifacts']}
            result=self.legacy.inspect_matrix(manifest,ROOT,decoded,'a'*40)
            self.assertEqual(set(result),self.legacy.PROFILES)
            for key in ('diagnostic_only','phase6_complete','native_admission_qualified'):
                changed=copy.deepcopy(manifest);changed[key]=True
                with self.assertRaises(ValueError):self.hosted.inspect_matrix(changed,ROOT,decoded,'a'*40)
            (next(iter(decoded.values()))/'extra.txt').write_text('not in ZIP')
            with self.assertRaises(ValueError):self.hosted.inspect_matrix(manifest,ROOT,decoded,'a'*40)

    def test_damaged_zip_source_and_unsafe_archive_members_are_rejected(self):
        for damage in ('zip','source','path'):
            with tempfile.TemporaryDirectory(dir=ROOT/'out') as tmp:
                root=Path(tmp);records=self.fixture_archives(root,'../escape.txt' if damage=='path' else 'identity.json')
                if damage=='zip':
                    p=root/(records['artifacts'][0]['name']+'.zip');p.write_bytes(p.read_bytes()+b'changed')
                elif damage=='source':records['artifacts'][0]['workflow_run']['head_sha']='b'*40
                with self.subTest(damage=damage),self.assertRaises(ValueError):
                    self.hosted.retain(records,root,root/'decoded')
                self.assertFalse((root/'escape.txt').exists())


if __name__=='__main__':unittest.main()
