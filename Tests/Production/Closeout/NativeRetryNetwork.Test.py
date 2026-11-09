"""The new reload bootstrap preserves HTTPS/signatures/versions and narrows its child guard."""
from pathlib import Path
import os
import subprocess
import unittest
from contracts import ROOT


class NativeRetryNetworkTests(unittest.TestCase):
    def test_only_the_new_explicit_reload_child_changes_from_the_complete_original_transport(self):
        old=(ROOT/'Tests/Production/Closeout/prepare_hosted_native_network.sh').read_text()
        new=(ROOT/'Tests/Production/Closeout/prepare_hosted_native_retry_network.sh').read_text()
        before='case "${1:-}" in Tests/Production/Closeout/prepare_hosted_native_retry_reload.sh) ;; *) exit 2;; esac'
        after='case "${1:-}" in Tests/Production/Closeout/prepare_hosted_native_writer_runtime.sh|Tests/Production/Closeout/prepare_hosted_native_reload.sh) ;; *) exit 2;; esac'
        self.assertEqual(new.count(before),1);self.assertEqual(new.replace(before,after),old)

    def test_other_children_fail_before_any_system_or_package_operation(self):
        script=ROOT/'Tests/Production/Closeout/prepare_hosted_native_retry_network.sh'
        for child in ('unexpected-child.sh','Tests/Production/Closeout/prepare_hosted_native_reload.sh'):
            result=subprocess.run(['bash',str(script),child],env=dict(os.environ,GITHUB_ACTIONS='true',RUNNER_OS='Linux',PROFILE='Debug-sse2'),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            self.assertEqual(result.returncode,2);self.assertEqual(result.stdout,b'')


if __name__=='__main__':unittest.main()
