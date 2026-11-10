"""Hosted negative controls preserve the original inputs and cannot grant wider acceptance."""
import ast
import copy
import json
from pathlib import Path
import tempfile
import unittest
from contracts import ROOT,atomic_json
import hosted_class_rejections as hosted
import capture_hosted_native_writer_runtime as original


class HostedClassRejectionTests(unittest.TestCase):
    def test_all_original_families_invalid_metadata_fixture_and_source_guards_are_frozen(self):
        lock=hosted.conserved_sources();controls=lock['exact_original_controls']
        self.assertEqual(len(controls),45);self.assertEqual(len(lock['source_sha256']),10)
        self.assertEqual(sum(v['variant']=='metadata' for v in controls),7)
        self.assertEqual(sum(v['variant'] in ('windows-pe','missing-query') for v in controls),2)
        self.assertEqual({v['family'] for v in controls},set(hosted.load(ROOT/'Tests/Production/RemainingStock/cases.json')['required_classes']))
        self.assertIn('Tests/Production/RemainingVessels/RejectedModule.cpp',lock['source_sha256'])

    def test_actual_normal_host_runtime_provider_post_guards_and_failure_retention_are_unchanged(self):
        before=original.prepared_body();after=hosted.prepared_body();ast.parse(after)
        end="        require(sha(ROOT/'out/mesa-topology-restoration/restoration.json')"
        self.assertIn(before[before.index(end):before.index("        report.update(status='captured-and-independently-audited-native-writers-only'")],after)
        self.assertIn("'--rejection-control'",after);self.assertIn("'--runtime-role','normal','--jobs','1'",after)
        self.assertIn("'--rejection-windows-dll',pe['dll']",after);self.assertIn("'Tests/Production/RemainingVessels/rejections.py'",after)
        self.assertNotIn("'--lifetime-sessions'",after)
        workflow=(ROOT/'.github/workflows/phase6-native-class-rejections.yml').read_text()
        self.assertIn('needs: readiness',workflow);self.assertIn('max-parallel: 2',workflow)
        self.assertIn('runs-on: ubuntu-24.04',workflow);self.assertIn('profile: [Debug-automatic, Debug-sse2, Release-automatic, Release-sse2]',workflow)
        self.assertIn('Preserve raw partial files if lossless packing itself failed',workflow)
        network=(ROOT/'Tests/Production/Closeout/prepare_hosted_class_rejections_network.sh').read_text()
        self.assertEqual(network.replace('prepare_hosted_class_rejections.sh','prepare_hosted_class_lifetimes.sh').replace('out/native-rejection-network/','out/native-class-network/'),(ROOT/'Tests/Production/Closeout/prepare_hosted_class_lifetimes_network.sh').read_text())

    def test_shortened_diagnostic_wrong_exit_unclean_or_duplicate_actual_processes_cannot_pass(self):
        lock=hosted.conserved_sources()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);capture_path=root/'rejections.json';audit_path=root/'audit.json';exe='/actual/orbiter-production'
            identity=dict(profile='Debug-automatic',runtime_source_commit=hosted.COMPILED,sanitizer_linked=True)
            controls={}
            for index,control in enumerate(lock['exact_original_controls'],1):
                p=root/control['id'];p.mkdir();argv=[exe,'--scenario',control['case']]
                atomic_json(p/'invocation.json',dict(argv=argv))
                atomic_json(p/'process-receipt.json',dict(actual_collector_pid=index,owned_process_identities=[dict(pid=index,start_ticks=index*10,argv=argv)]))
                controls[control['id']]=dict(actual_exitcode=1,lifecycle=dict(rendered_frames=0,successful_presents=0,context_deleted=True))
            capture=dict(status='passed-negative-loader-and-class-controls-only',failures={},controls_requested=lock['exact_original_controls'],cases_requested=hosted.CASES,
                runtime_identity=identity,runtime_role='normal',runtime_executable=exe,controls=controls,diagnostic_only=True,native_admission_qualified=False,phase6_complete=False)
            def write(c):
                atomic_json(capture_path,c)
                audit=dict(status='audited-negative-loader-and-class-controls-only',runtime_identity=identity,capture_sha256=hosted.sha(capture_path),
                    actual_processes=45,runtime_role='normal',owning_bytes_unchanged=True,sanitizer_suppressions=False,controls=copy.deepcopy(c['controls']),
                    diagnostic_only=True,native_admission_qualified=False,phase6_complete=False);atomic_json(audit_path,audit)
            write(capture);result=hosted.inspect_profile('Debug-automatic',capture_path,audit_path)
            self.assertEqual(result['actual_original_processes'],45);self.assertTrue(result['published_raw_independent_replay_pending']);self.assertFalse(result['phase6_complete'])
            first=lock['exact_original_controls'][0]['id']
            for mutate in (lambda c:c.update(runtime_role='diagnostic'),lambda c:c['controls_requested'].pop(),
                           lambda c:c['controls'][first].update(actual_exitcode=0),
                           lambda c:c['controls'][first]['lifecycle'].update(successful_presents=1),lambda c:c.update(phase6_complete=True)):
                value=copy.deepcopy(capture);mutate(value);write(value)
                with self.assertRaises(ValueError):hosted.inspect_profile('Debug-automatic',capture_path,audit_path)
            write(capture)
            second=lock['exact_original_controls'][1]['id']
            first_receipt=hosted.load(root/first/'process-receipt.json')
            atomic_json(root/second/'process-receipt.json',first_receipt)
            with self.assertRaises(ValueError):hosted.inspect_profile('Debug-automatic',capture_path,audit_path)
