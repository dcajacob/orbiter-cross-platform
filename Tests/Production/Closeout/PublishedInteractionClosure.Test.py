"""Published interaction witness closure must preserve every exact file and pending acceptance gate."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from contracts import ROOT
import verify_published_class_interactions as published


class PublishedInteractionClosureTests(unittest.TestCase):
    def fixture(self,role):return json.loads((ROOT/('Tests/Production/Closeout/published-interaction-'+role+'-api.fixture.json')).read_text())

    def test_complete_closed_metadata_and_file_witness_API_identities_are_required(self):
        lock=published.load(published.LOCK)
        for role in ('metadata','witness'):
            original=self.fixture(role);pin=lock['profiles']['Debug-automatic'][role];before=copy.deepcopy(original)
            published.closed.validate_api(original,pin);self.assertEqual(original,before)
            for mutate in (lambda r:r['jobs'].pop(),lambda r:r['jobs'][0].update(labels=['self-hosted']),
                           lambda r:r['jobs'][0].update(conclusion='failure'),lambda r:r['run'].update(status='in_progress'),
                           lambda r:r['artifact'].update(digest='sha256:'+'0'*64),lambda r:r['artifact'].update(size_in_bytes=1)):
                value=copy.deepcopy(original);mutate(value)
                with self.assertRaises(ValueError):published.closed.validate_api(value,pin)

    def manifest(self):
        raw={'original/a':dict(sha256='a'*64,bytes=10),'original/b':dict(sha256='a'*64,bytes=10),'original/c':dict(sha256='b'*64,bytes=3)}
        proof=dict(actual_raw_members=3,actual_raw_decoded_bytes=23,complete_original_storage=dict(unique_file_contents=2,unique_materialized_bytes=13,complete_logical_bytes=23,all_logical_members_retained=True,duplicate_file_contents_shared_by_hardlink=True,raw_content_or_capture_records_rewritten=False))
        return raw,proof

    def test_manifest_cannot_drop_change_redirect_or_relabel_any_original_member(self):
        raw,proof=self.manifest();before=copy.deepcopy((raw,proof));self.assertEqual(published.verify_manifest(raw,proof)['logical_bytes'],23);self.assertEqual((raw,proof),before)
        for mutate in (lambda r,p:r.pop('original/a'),lambda r,p:r['original/a'].update(bytes=11),
                       lambda r,p:r['original/a'].update(sha256='not-a-digest'),lambda r,p:r.update({'../outside':r.pop('original/a')}),
                       lambda r,p:r.update({'ORIGINAL/A':r['original/a']}),lambda r,p:p['complete_original_storage'].update(unique_file_contents=3),
                       lambda r,p:p['complete_original_storage'].update(raw_content_or_capture_records_rewritten=True)):
            r,p=copy.deepcopy((raw,proof));mutate(r,p)
            with self.assertRaises(ValueError):published.verify_manifest(r,p)

    def test_exact_original_file_hash_and_complete_full_frame_length_are_both_required(self):
        raw,_=self.manifest();published.witness(raw,'original/a','a'*64,10)
        for name,digest,size in [('missing','a'*64,10),('original/a','b'*64,10),('original/a','a'*64,9)]:
            with self.assertRaises(ValueError):published.witness(raw,name,digest,size)

    def test_publication_verifier_imports_without_simulator_or_large_raw_inputs(self):
        result=subprocess.run([sys.executable,'-B',str(ROOT/'Tests/Production/Closeout/verify_published_class_interactions.py'),'--help'],
                              cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('--inputs',result.stdout)
