"""Hosted API refresh must retain the old provider guards and both genuine outcomes."""
import ast
import copy
import json
from pathlib import Path
import tempfile
import unittest
from contracts import ROOT
import hosted_native_general_api as api


class HostedGeneralApiTests(unittest.TestCase):
    def test_provider_and_userspace_setup_and_all_post_capture_guards_are_conserved(self):
        old=api.runtime_writer.prepared_body();new=api.prepared_body();ast.parse(new)
        old_start=old.index("        build=ROOT/'out/phase6-hosted-native'/a.profile;capture=")
        new_start=new.index('        from hosted_native_general_api import source_identity,inspect_audit')
        prefix=new[:new_start].replace("protocol='phase6-hosted-native-general-api-v1'","protocol='phase6-hosted-native-stock-writer-runtime-v3'").replace("ROOT/'out/hosted-native-api'","ROOT/'out/hosted-native-writer'").replace("ROOT/'out/native-api-container.json'","ROOT/'out/native-writer-container.json'")
        self.assertEqual(prefix,old[:old_start])
        anchor="        require(sha(ROOT/'out/mesa-topology-restoration/restoration.json')"
        end="        report.update(status="
        self.assertEqual(new[new.index(anchor):new.index(end,new.index(anchor))],
                         old[old.index(anchor):old.index(end,old.index(anchor))])
        self.assertNotIn('all-38-stock-writers-twice',new)
        self.assertNotIn('RemainingStockPersistence/capture_native.py',new)
        self.assertIn("'GeneralApiCorrection/capture_native.py'",new.replace("Tests/Production/",""))
        self.assertIn("'--variant-version','v2'",new)

    def test_actual_full_common_core_and_every_original_api_guard_are_frozen(self):
        proof=api.source_identity()
        self.assertEqual(proof['complete_locked_source_count'],623)
        self.assertTrue(proof['actual_core_sources_identical'])
        self.assertFalse(proof['retained_runtime_relabelled'])
        self.assertEqual(set(proof['original_api_sources_sha256']),{api.API+n for n in api.CONSERVED})

    def test_transport_and_bootstrap_retain_all_original_trust_and_exact_package_rules(self):
        parent=ROOT/'Tests/Production/Closeout'
        original=(parent/'prepare_hosted_native_writer_runtime.sh').read_text()
        self.assertEqual((parent/'prepare_hosted_native_general_api.sh').read_text(),
                         original.replace('capture_hosted_native_writer_runtime.py','hosted_native_general_api.py'))
        original=(parent/'prepare_hosted_native_network.sh').read_text()
        expected=original.replace('Tests/Production/Closeout/prepare_hosted_native_writer_runtime.sh|Tests/Production/Closeout/prepare_hosted_native_reload.sh',
                                  'Tests/Production/Closeout/prepare_hosted_native_general_api.sh').replace('out/native-runtime-network/','out/native-api-network/')
        self.assertEqual((parent/'prepare_hosted_native_general_api_network.sh').read_text(),expected)

    def test_incomplete_or_relabelled_or_mutated_actual_api_evidence_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            capture=Path(directory);evidence=capture/'actual.log';evidence.write_bytes(b'original retained actual fixture bytes')
            identity=dict(runtime_source_commit=api.RUNTIME,profile='Debug-automatic',sanitizer_linked=True)
            cases={k:dict(process=dict(actual_collector_pid=i,terminal=True,actual_returncode=0,cancelled=False))
                   for k,i in (('original',101),('corrected',102))}
            diagnostic=dict(status='captured-original-and-corrected-native-diagnostic-only',runtime_identity=identity,cases=cases)
            observed={k:dict(actual_pid=cases[k]['process']['actual_collector_pid'],returncode=0,completed_pass_markers=n)
                      for k,n in (('original',10),('corrected',11))}
            audit=dict(status='passed-native-api-script-diagnostic-only',runtime_identity=identity,observed=observed,
                       startup_exit_policy_audited=True,normal_admission_qualified=False,phase6_complete=False,
                       evidence_sha256={str(evidence):api.sha(evidence)})
            source=capture/'diagnostic.json';target=capture/'audit.json'
            source.write_text(json.dumps(diagnostic));target.write_text(json.dumps(audit))
            result=api.inspect_audit(capture,target,'Debug-automatic')
            self.assertEqual(result['actual_processes'],2);self.assertFalse(result['complete_general_api_qualification'])
            for mutate in (lambda r:r.update(status='running'),lambda r:r.update(startup_exit_policy_audited=False),
                           lambda r:r['runtime_identity'].update(sanitizer_linked=False),
                           lambda r:r['runtime_identity'].update(runtime_source_commit='f'*40),
                           lambda r:r['observed']['original'].update(completed_pass_markers=11),
                           lambda r:r['observed']['corrected'].update(completed_pass_markers=10),
                           lambda r:r['observed']['corrected'].update(actual_pid=101),
                           lambda r:r.update(normal_admission_qualified=True),
                           lambda r:r['evidence_sha256'].clear()):
                changed=copy.deepcopy(audit);mutate(changed);target.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):api.inspect_audit(capture,target,'Debug-automatic')
            target.write_text(json.dumps(audit));evidence.write_bytes(b'changed after independent audit')
            with self.assertRaises(ValueError):api.inspect_audit(capture,target,'Debug-automatic')

    def test_fresh_lane_has_only_standard_runners_and_retains_every_partial_result(self):
        workflow=(ROOT/'.github/workflows/phase6-native-general-api.yml').read_text()
        self.assertEqual(workflow.count('runs-on: ubuntu-24.04'),2)
        self.assertIn('max-parallel: 2',workflow);self.assertIn('cancel-in-progress: false',workflow)
        self.assertIn('configuration: [Debug, Release]',workflow);self.assertIn('math_profile: [automatic, sse2]',workflow)
        self.assertIn('out/native-general-api-capture/${{ env.PROFILE }}/**',workflow)
        self.assertIn('out/native-api-source/*/*.body',workflow)
        self.assertIn('ca-certificates.crt:/run/orbiter-ci-system-ca.pem:ro',workflow)
        for forbidden in ('self-hosted','windows-2022','larger','continue-on-error','detect_leaks=0'):
            self.assertNotIn(forbidden,workflow)


if __name__=='__main__':unittest.main()
