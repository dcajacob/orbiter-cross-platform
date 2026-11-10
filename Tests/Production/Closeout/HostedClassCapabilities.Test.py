"""Ensure hosted capability transport preserves the original full runtime and comparison contract."""
import ast
import unittest
from contracts import ROOT
import hosted_class_capabilities as hosted
import capture_hosted_native_writer_runtime as runtime


class HostedClassCapabilitiesTests(unittest.TestCase):
    def test_all_original_sources_runtime_setup_and_post_capture_guards_are_conserved(self):
        self.assertEqual(len(hosted.sources()),8)
        original=runtime.prepared_body();actual=hosted.prepared_body();ast.parse(actual)
        start="        build=ROOT/'out/phase6-hosted-native'/a.profile;capture="
        end="        require(sha(ROOT/'out/mesa-topology-restoration/restoration.json')"
        prefix=original[:original.index(start)].replace("protocol='phase6-hosted-native-stock-writer-runtime-v3'","protocol='phase6-hosted-native-class-capabilities-v1'").replace("ROOT/'out/hosted-native-writer'","ROOT/'out/hosted-native-class-capabilities'").replace("ROOT/'out/native-writer-container.json'","ROOT/'out/native-capability-container.json'")
        self.assertEqual(actual[:actual.index('        from hosted_native_general_api import source_identity')],prefix)
        self.assertIn(original[original.index(end):original.index("        report.update(status='captured-and-independently-audited-native-writers-only'")],actual)
        self.assertIn("'--capability-control'",actual);self.assertIn("'--repeats','2'",actual)
        self.assertIn("'--runtime-role','diagnostic','--jobs','1'",actual)
        self.assertIn("'--windows-reference',reference['capture']",actual)
        self.assertIn("'--windows-build',reference['build']",actual)
        self.assertIn("'--preserved',reference['preserved']",actual)
        self.assertIn('verify(reference)',actual)
        self.assertEqual(len(hosted.CASES)*2*2*4,144)

    def test_network_and_bootstrap_preserve_verified_versions_trust_and_failure_behavior(self):
        folder=ROOT/'Tests/Production/Closeout'
        actual=(folder/'prepare_hosted_class_capabilities.sh').read_bytes()
        original=(folder/'prepare_hosted_class_lifetimes.sh').read_bytes()
        self.assertEqual(actual.replace(b'hosted_class_capabilities.py',b'hosted_class_lifetimes.py'),original)
        actual=(folder/'prepare_hosted_class_capabilities_network.sh').read_text()
        original=(folder/'prepare_hosted_class_lifetimes_network.sh').read_text()
        self.assertEqual(actual.replace('Tests/Production/Closeout/prepare_hosted_class_capabilities.sh','Tests/Production/Closeout/prepare_hosted_class_lifetimes.sh|Tests/Production/Closeout/prepare_hosted_class_userspace.sh').replace('out/native-capability-network/','out/native-class-network/'),original)
        self.assertIn('APT::Snapshot "20261109T212432Z";',actual)
