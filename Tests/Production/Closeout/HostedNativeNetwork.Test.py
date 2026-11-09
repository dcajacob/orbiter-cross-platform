"""Package transport changes only Ubuntu's HTTP scheme and preserves source and trust guards."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from contracts import ROOT


class HostedNativeNetworkTests(unittest.TestCase):
    def test_actual_source_rewrite_keeps_suites_signing_keys_components_and_existing_https(self):
        script=(ROOT/'Tests/Production/Closeout/prepare_hosted_native_network.sh').read_text()
        start=script.index('rewrite_source() {');end=script.index('\n}\n',start)+3;function=script[start:end]
        for scheme in ('http','https'):
            original=f'Types: deb\nURIs: {scheme}://archive.ubuntu.com/ubuntu/\nSuites: resolute resolute-updates\nComponents: main universe\nSigned-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n\nURIs: http://security.ubuntu.com/ubuntu\nSuites: resolute-security\n'
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);before=root/'before';after=root/'after';before.write_text(original)
                subprocess.run(['bash','-euo','pipefail','-c',function+'\nrewrite_source "$1" "$2"','fixture',str(before),str(after)],check=True)
                self.assertEqual(before.read_text(),original)
                self.assertEqual(after.read_text(),original.replace('http://archive.ubuntu.com/ubuntu','https://archive.ubuntu.com/ubuntu').replace('http://security.ubuntu.com/ubuntu','https://security.ubuntu.com/ubuntu'))
        self.assertIn('Acquire::https::CaInfo "/run/orbiter-ci-system-ca.pem";',script)
        self.assertIn('APT::Update::Error-Mode "any";',script);self.assertIn('Acquire::Retries "3";',script)
        for value in ('Verify-Peer "false"','Verify-Host "false"','AllowUnauthenticated','trusted=yes'):self.assertNotIn(value,script)

    def test_network_lanes_preserve_active_previous_jobs_and_the_same_capture_and_signed_image(self):
        text=(ROOT/'.github/workflows/phase6-native-runtime-network-writers.yml').read_text()
        for config in ('debug','release'):
            for mode in ('automatic','sse2'):self.assertIn('qualification/native-runtime-writer-'+config+'-'+mode+'-v2',text)
        self.assertIn("if(prior.some(r=>r.status!=='completed'))",text)
        self.assertIn("found[0].status!=='completed'",text);self.assertIn("found[0].conclusion!=='failure'",text)
        self.assertIn('ca-certificates.crt:/run/orbiter-ci-system-ca.pem:ro',text)
        self.assertIn('prepare_hosted_native_network.sh Tests/Production/Closeout/prepare_hosted_native_writer_runtime.sh',text)
        self.assertIn('docker run --rm --init --cpus=2 --shm-size=1g',text);self.assertIn('cancel-in-progress: false',text)
        self.assertNotIn('math_profile: [automatic, sse2]',text);self.assertNotIn('--case',text)
        reload=(ROOT/'.github/workflows/phase6-native-stock-reloads.yml').read_text()
        self.assertIn('prepare_hosted_native_network.sh Tests/Production/Closeout/prepare_hosted_native_reload.sh',reload)
        self.assertIn('a13bae582c7de0c9b6e2fd0c064b1a3ea12e85c7',reload)


if __name__=='__main__':unittest.main()
