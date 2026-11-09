"""Actual byte materialization and provenance rejection controls, with no qualification credit."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import sys
import unittest
from contracts import ROOT
sys.path.insert(0,str(ROOT/'Tests/Production/GeneralApiCorrection/Hosted'))
import joint_api_qualification as joint


class JointGeneralApiTests(unittest.TestCase):
    def test_exact_actual_complete_source_API_is_required(self):
        record=json.loads((Path(__file__).parent/'joint-api-input.fixture.json').read_text())
        self.assertEqual(joint.validate_input('windows-final-Debug',record)['artifact_id'],13720100926)
        for mutate in (lambda r:r['run'].update(head_sha='f'*40),lambda r:r['run'].update(conclusion='failure'),
                       lambda r:r['run'].update(run_attempt=2),lambda r:r['jobs'].pop(),lambda r:r['jobs'][0].update(conclusion='failure'),
                       lambda r:r['jobs'][0].update(labels=['self-hosted','ubuntu-24.04']),lambda r:r['artifact'].update(digest='sha256:'+'0'*64),
                       lambda r:r['artifact'].update(size_in_bytes=1),lambda r:r['artifact'].update(expired=True)):
            changed=copy.deepcopy(record);mutate(changed)
            with self.assertRaises(ValueError):joint.validate_input('windows-final-Debug',changed)

    def test_conflicting_old_windows_paths_get_distinct_real_actual_byte_namespaces(self):
        old='D:\\a\\orbiter-cross-platform\\orbiter-cross-platform\\out\\sdk.zip'
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);outcomes=[]
            for configuration,body in (('Debug',b'actual-debug-bytes'),('Release',b'actual-release-bytes')):
                original=dict(status='passed-current-Windows-api-diagnostic-only',github=dict(run_id=123,collector_commit='a'*40),
                    evidence_sha256={old:hashlib.sha256(body).hexdigest()},actual_processes=8,results=dict(original='original-failure-preserved'))
                raw=json.dumps(original).encode()
                path,scope=joint.materialize_audit(raw,'windows-'+configuration,base/configuration,lambda name:(body,dict(kind='disposable-actual-bytes')),dict(test_only=True))
                derived=json.loads(path.read_text());self.assertEqual((base/configuration/'original-audit.json').read_bytes(),raw)
                self.assertEqual(derived['results'],original['results']);self.assertEqual(derived['github'],original['github'])
                self.assertEqual(derived['original_evidence_sha256'],original['evidence_sha256'])
                name=next(iter(derived['evidence_sha256']));self.assertEqual(Path(name).read_bytes(),body)
                self.assertNotIn(old,derived['evidence_sha256']);outcomes.append(name)
            self.assertNotEqual(outcomes[0],outcomes[1])

    def test_expected_digest_lookup_cannot_replace_an_actual_byte_read(self):
        body=b'actual bytes';digest=hashlib.sha256(body).hexdigest();raw=json.dumps(dict(evidence_sha256={'original':digest})).encode()
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            for index,fake in enumerate((digest,dict(sha256=digest),b'changed bytes')):
                with self.assertRaises(ValueError):joint.materialize_audit(raw,'windows-Debug',base/str(index),lambda name:(fake,{}),{})
            failure=json.loads((base/'2/materialization-failure.json').read_text())
            self.assertEqual(failure['expected_sha256'],digest)
            self.assertEqual((base/'2/evidence-0000.bin').read_bytes(),b'changed bytes')

    def test_original_qualifier_and_all_existing_guards_are_conserved(self):
        self.assertEqual(joint.sha(Path(joint.qualification.__file__)),joint.QUALIFIER_SHA256)
        source=Path(joint.qualification.__file__).read_text()
        self.assertIn("'Conflicting API evidence digest'",source)
        self.assertIn("all(sha(p)==value for p,value in evidence.items())",source)
        self.assertIn("selected[0]['discovered_tests']==18",source)
        self.assertIn("helper['actual_lua_controls']==26",source)
        self.assertIn("helper['rejected_damaged_inputs']==3",source)
