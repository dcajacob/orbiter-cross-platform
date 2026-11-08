"""Provider build results cannot waive missing controls or change their producer."""
import json
from pathlib import Path
import re
import tempfile
import unittest
from contracts import ROOT
from seal_hosted_native_providers import control_status


class HostedNativeProvidersTests(unittest.TestCase):
    def test_only_complete_bound_controls_can_qualify_dependency_builds(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);producer='a'*40;image='ubuntu@sha256:'+'b'*64
            for name in ('fontconfig','gdk','mesa'):
                path=base/(name+'-controls');path.mkdir();(path/('report.json' if name=='mesa' else 'verification.json')).write_text('{"status":"passed"}')
            marker=base/'completed.json';good=dict(status='completed-existing-dependency-controls-only',source_commit=producer,container_digest=image,phase6_complete=False)
            self.assertFalse(control_status(base,producer,image)[0]);marker.write_text(json.dumps(good))
            self.assertTrue(control_status(base,producer,image)[0])
            for key,value in (('source_commit','c'*40),('container_digest','ubuntu:latest'),('phase6_complete',True)):
                altered=good|{key:value};marker.write_text(json.dumps(altered));self.assertFalse(control_status(base,producer,image)[0])
            marker.write_text(json.dumps(good));(base/'gdk-controls/verification.json').write_text('{"status":"failed"}')
            self.assertFalse(control_status(base,producer,image)[0])

    def test_matching_userspace_is_pinned_on_a_standard_runner(self):
        lock=json.loads((ROOT/'Tests/Production/Closeout/native-provider-container.lock.json').read_text())
        self.assertEqual(lock['repository'],'docker.io/library/ubuntu');self.assertEqual(lock['platform'],'linux/amd64')
        self.assertRegex(lock['image_digest'],r'^sha256:[0-9a-f]{64}$')
        body=(ROOT/'.github/workflows/phase6-native-providers.yml').read_text()
        self.assertIn('runs-on: ubuntu-24.04',body);self.assertIn('--cpus=2',body)
        self.assertIn('-v "$GITHUB_WORKSPACE:$GITHUB_WORKSPACE"',body)
        self.assertNotIn('--privileged',body)

    def test_existing_sanitizer_and_genuine_leak_controls_are_required(self):
        body=(ROOT/'Tests/Production/Closeout/build_hosted_native_providers.sh').read_text()
        for path in ('FontConfigLifetime/qualify.py','GdkLifetime/qualify.py','GraphicsDriverLifetime/allocator_test.py','WaylandInput/prepare.py'):
            self.assertIn(path,body)
        self.assertIn('--sanitizers --baseline',body);self.assertIn('--sanitizers --jobs 2',body)
        for disabled in ('detect_leaks=0','suppressions=','halt_on_error=0'):
            self.assertNotIn(disabled,body)


if __name__=='__main__':unittest.main()
