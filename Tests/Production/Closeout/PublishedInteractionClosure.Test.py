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

    def test_single_file_upload_uses_its_original_basename_without_rewriting_any_witness_byte(self):
        import hashlib
        raw,_=self.manifest();body=json.dumps(raw,indent=2).encode();digest=hashlib.sha256(body).hexdigest()
        bodies={'raw-members.json':body};members={'raw-members.json':digest};before=copy.deepcopy((bodies,members))
        self.assertEqual(published.manifest_payload(bodies,members,digest),raw);self.assertEqual((bodies,members),before)
        for b,m,d in [({'interaction-independent/Debug-automatic/raw-members.json':body},{'interaction-independent/Debug-automatic/raw-members.json':digest},digest),
                      (bodies,members,'0'*64),({'raw-members.json':body+b' '},members,digest),
                      (dict(bodies,extra=body),dict(members,extra=digest),digest)]:
            with self.assertRaises(ValueError):published.manifest_payload(b,m,d)

    def test_complete_source_owned_interaction_guard_roster_includes_every_new_guard(self):
        expected=published.load(published.LOCK)['original_reference_guards']['Debug-automatic']
        reference=dict(old_reference_owner=expected['original_capture_source'],old_guarded_inputs={name:dict(sha256=value) for name,value in expected['exact_guarded_paths_sha256'].items()})
        before=copy.deepcopy(reference);self.assertEqual(published.verify_reference_roster(reference,'Debug-automatic'),306);self.assertEqual(reference,before)
        original_name=next(iter(reference['old_guarded_inputs']))
        for mutate in (lambda r:r['old_guarded_inputs'].pop(original_name),lambda r:r['old_guarded_inputs'][original_name].update(sha256='0'*64),
                       lambda r:r['old_guarded_inputs'].update({'substituted':r['old_guarded_inputs'].pop(original_name)}),
                       lambda r:r.update(old_reference_owner='e'*40)):
            value=copy.deepcopy(reference);mutate(value)
            with self.assertRaises(ValueError):published.verify_reference_roster(value,'Debug-automatic')

    def test_publication_verifier_imports_without_simulator_or_large_raw_inputs(self):
        result=subprocess.run([sys.executable,'-B',str(ROOT/'Tests/Production/Closeout/verify_published_class_interactions.py'),'--help'],
                              cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('--inputs',result.stdout)


    def test_each_immutable_replay_owner_requires_all_of_its_original_controls(self):
        relative='Tests/Production/Closeout/contracts.py'
        for source,count in published.REPLAY_CONTROL_COUNTS.items():
            value=dict(status='passed',tests_run=count,producer_commit=source,sources_match_producer=True,
                       failures=0,errors=0,skipped=0,sources_sha256={str(published.CI/relative):published.closed.gitsha(source,relative)})
            bodies={'published-interaction-controls.json':json.dumps(value).encode()};before=copy.deepcopy(bodies)
            published.replay_controls(bodies,source);self.assertEqual(bodies,before)
            for mutate in (lambda v:v.update(tests_run=count-1),lambda v:v.update(tests_run=count+1),
                           lambda v:v.update(producer_commit='0'*40),lambda v:v.update(skipped=1),
                           lambda v:v['sources_sha256'].update({str(published.CI/relative):'0'*64})):
                changed=copy.deepcopy(value);mutate(changed)
                with self.assertRaises(ValueError):published.replay_controls({'published-interaction-controls.json':json.dumps(changed).encode()},source)
            with self.assertRaises(ValueError):published.replay_controls(bodies,'f'*40)

    def test_complete_release_publication_API_cannot_borrow_Debug_source_or_control_owner(self):
        lock=published.load(published.FOUR_PROFILE_LOCK)
        for role in ('metadata','witness'):
            original=json.loads((ROOT/('Tests/Production/Closeout/published-interaction-Release-'+role+'-api.fixture.json')).read_text())
            pin=lock['profiles']['Release-automatic'][role];before=copy.deepcopy(original)
            published.closed.validate_api(original,pin);self.assertEqual(original,before)
            for mutate in (lambda r:r['run'].update(head_sha='2f98af3e37b8b5b79d951c82ba51aabd51618768'),
                           lambda r:r['jobs'].pop(),lambda r:r['jobs'][0].update(labels=['self-hosted']),
                           lambda r:r['artifact'].update(digest='sha256:'+'0'*64)):
                value=copy.deepcopy(original);mutate(value)
                with self.assertRaises(ValueError):published.closed.validate_api(value,pin)

    def test_four_profile_lock_preserves_Debug_pins_and_every_exact_Release_reference_guard(self):
        old=published.load(published.LOCK);new=published.load(published.FOUR_PROFILE_LOCK)
        self.assertEqual(set(new['profiles']),set(published.PROFILES))
        for profile in old['profiles']:
            self.assertEqual(new['profiles'][profile],old['profiles'][profile])
            self.assertEqual(new['original_reference_guards'][profile],old['original_reference_guards'][profile])
        for profile in new['profiles']:
            expected=new['original_reference_guards'][profile]
            reference=dict(old_reference_owner=expected['original_capture_source'],old_guarded_inputs={name:dict(sha256=value) for name,value in expected['exact_guarded_paths_sha256'].items()})
            self.assertEqual(published.verify_reference_roster(reference,profile,published.FOUR_PROFILE_LOCK),306)
            reference['old_guarded_inputs'].pop(next(iter(reference['old_guarded_inputs'])))
            with self.assertRaises(ValueError):published.verify_reference_roster(reference,profile,published.FOUR_PROFILE_LOCK)

    def test_interaction_facet_requires_complete_distinct_four_profile_scope_and_pending_acceptance(self):
        lock=published.load(published.FOUR_PROFILE_LOCK);raw=published.load(published.replay.LOCK)
        profiles={profile:dict(profile=profile,actual_original_processes=18,complete_flows=9,repeats=2,
            actual_original_successful_presents=14048,compiled_runtime_source=published.replay.original.COMPILED,
            original_capture_source=raw['source'],original_capture_job_id=pin['job_id'],original_raw_artifact_id=pin['artifact_id'],
            all_five_original_audits_byte_identical=True,all_original_source_reference_guards_preserved=True,
            original_source_reference_guard_count=306,new_simulator_processes=0,new_X11_processes=0,
            **{k:False for k in published.FLAGS}) for profile,pin in raw['profiles'].items()}
        before=copy.deepcopy(profiles);result=published.interaction_facet(profiles,lock)
        self.assertEqual(profiles,before);self.assertEqual(result['actual_original_processes'],72)
        self.assertEqual(result['actual_original_successful_presents'],56192);self.assertEqual(result['passed_class_facets'],['interactions'])
        self.assertTrue(all(result[k] is False for k in published.FLAGS))
        first,second=published.PROFILES[:2]
        for mutate in (lambda p:p.pop(first),lambda p:p[first].update(actual_original_processes=17),
                       lambda p:p[first].update(repeats=1),lambda p:p[first].update(actual_original_successful_presents=14047),
                       lambda p:p[first].update(original_capture_job_id=p[second]['original_capture_job_id']),
                       lambda p:p[first].update(original_raw_artifact_id=p[second]['original_raw_artifact_id']),
                       lambda p:p[first].update(all_five_original_audits_byte_identical=False),
                       lambda p:p[first].update(original_source_reference_guard_count=293),
                       lambda p:p[first].update(phase6_complete=True)):
            value=copy.deepcopy(profiles);mutate(value)
            with self.assertRaises(ValueError):published.interaction_facet(value,lock)
