from unittest import TestCase
import original_package_snapshot_fallback as f
import subprocess


class OriginalSnapshotFallback(TestCase):
    def test_only_one_transport_call_changes(self):
        original=f.ORIGINAL.read_text();body=f.prepared_body()
        self.assertEqual(body.replace(f.REPLACEMENT,f.ANCHOR,1),original)
        self.assertEqual(body.count(f.REPLACEMENT),1)

    def test_fallback_retains_strong_hash_exact_original_URI_and_failed_receipts(self):
        body=f.prepared_body()
        self.assertIn('download-file "$original" "$cache" "SHA256:$expected"',body)
        self.assertIn('preserved-original-pool-failures.tsv',body)
        self.assertIn('exact-original-snapshot-blob-$count',body)
        self.assertIn('test "$(stat -c',body)
        self.assertIn('test "$actual" = "$expected"',body)
        self.assertIn('apt-get --no-download install',body)
        self.assertNotIn('AllowUnauthenticated',body)
        self.assertNotIn('Verify-Peer=false',body)

    def test_prepared_shell_is_valid_without_running_package_tools(self):
        self.assertEqual(subprocess.run(['bash','-n'],input=f.prepared_body(),text=True,capture_output=True).returncode,0)

    def test_minimal_container_needs_no_python_before_exact_package_installation(self):
        from pathlib import Path
        workflow=(f.ROOT/'.github/workflows/phase6-native-numerical-observer-equivalence.yml').read_text()
        self.assertLess(workflow.index('original_package_snapshot_fallback.py --prepare-only'),workflow.index('docker run --rm'))
        bootstrap=(f.ROOT/'Tests/Production/Closeout/prepare_hosted_numerical_observer.sh').read_text()
        self.assertLess(bootstrap.index('bash out/numerical-observer-pool-source'),bootstrap.index('python3'))
        self.assertEqual(bootstrap.count('sha256sum --check out/numerical-observer-pool-source'),2)
