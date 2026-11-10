"""Conserve complete original class lifetime tests and truthful hosted provenance."""
import ast
from pathlib import Path
import sys
import unittest
from contracts import ROOT
import hosted_class_lifetimes as hosted
import capture_hosted_native_writer_runtime as runtime


class HostedClassLifetimesTests(unittest.TestCase):
    def test_every_original_class_collector_auditor_and_finite_world_count_is_conserved(self):
        result=hosted.conserved_sources()
        self.assertEqual(len(result['family_cases']),11);self.assertEqual(len(result['selected_complete_scenes']),7)
        self.assertEqual(result['frames_per_world'],60);self.assertEqual(result['worlds_per_scene'],20);self.assertEqual(result['paused_worlds'],20)

    def test_original_paused_body_changes_only_truthful_new_capture_transport_flags(self):
        original=(ROOT/'Tests/Production/RemainingVessels/paused_attachments.py').read_text()
        actual=hosted.paused_body();ast.parse(actual)
        self.assertEqual(actual.replace('cloud_builds_used=True, raw_evidence_uploaded=False','cloud_builds_used=False, raw_evidence_uploaded=False'),original)
        self.assertIn("for index in range(1, args.worlds + 1)",actual)
        self.assertIn("sanitizer_suppressions=False",actual)

    def test_original_runtime_setup_and_all_post_source_provider_guards_are_retained(self):
        original=runtime.prepared_body();actual=hosted.prepared_body();ast.parse(actual)
        start="        build=ROOT/'out/phase6-hosted-native'/a.profile;capture="
        end="        require(sha(ROOT/'out/mesa-topology-restoration/restoration.json')"
        self.assertEqual(actual[:actual.index('        from hosted_native_general_api import source_identity')],
            original[:original.index(start)].replace("protocol='phase6-hosted-native-stock-writer-runtime-v3'","protocol='phase6-hosted-native-class-lifetimes-v1'").replace("ROOT/'out/hosted-native-writer'","ROOT/'out/hosted-native-class-lifetimes'").replace("ROOT/'out/native-writer-container.json'","ROOT/'out/native-class-container.json'"))
        self.assertIn(original[original.index(end):original.index("        report.update(status='captured-and-independently-audited-native-writers-only'")],actual)
        self.assertIn("'--lifetime-sessions','20'",actual);self.assertIn("'--worlds','20'",actual)
        self.assertIn("'--jobs','1'",actual)
        network=(ROOT/'Tests/Production/Closeout/prepare_hosted_class_lifetimes_network.sh').read_text()
        old=(ROOT/'Tests/Production/Closeout/prepare_hosted_native_general_api_network.sh').read_text()
        self.assertEqual(network.replace('out/native-class-network/','out/native-api-network/').replace('prepare_hosted_class_lifetimes.sh','prepare_hosted_native_general_api.sh'),old)
