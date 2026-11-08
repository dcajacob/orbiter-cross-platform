#!/usr/bin/env python3
"""Hosted setup is explicit; existing simulation commands and controls are conserved."""
from pathlib import Path
import subprocess
import unittest

from contracts import ROOT, load


class HostedCampaignTests(unittest.TestCase):
    def test_reused_checks_conserve_commands_with_explicit_provisioner_and_crt_host(self):
        for name in ('production-client.yml', 'matched-clock-remaining-stock-full.yml', 'native-production-client.yml'):
            path = '.github/workflows/' + name
            before = subprocess.check_output(['git', '-C', str(ROOT), 'show', 'bee7e1c1:' + path])
            after = (ROOT / path).read_bytes()
            expected = before.split(b'\njobs:\n', 1)[1].replace(
                b'Tests/Production/prepare_data.py', b'Tests/Production/prepare_hosted_data.py')
            self.assertEqual(expected.count(b'runs-on: windows-2022'), 1)
            expected = expected.replace(b'runs-on: windows-2022', b'runs-on: windows-2025')
            selector = b"          vsversion: '17.0'\n"
            self.assertEqual(expected.count(selector), 1)
            expected = expected.replace(selector, b'')
            if name == 'production-client.yml':
                configure = b'-B out/runtime-rebuild -G Ninja -DCMAKE_BUILD_TYPE=${{ matrix.configuration }} '
                self.assertEqual(expected.count(configure), 1)
                expected = expected.replace(configure, configure + b'"-DCMAKE_POLICY_VERSION_MINIMUM=3.5" ')
                existing_policy = b' -DCMAKE_POLICY_VERSION_MINIMUM=3.5 '
                self.assertEqual(expected.count(existing_policy), 1)
                expected = expected.replace(existing_policy, b' "-DCMAKE_POLICY_VERSION_MINIMUM=3.5" ')
            self.assertEqual(expected, after.split(b'\njobs:\n', 1)[1], name)
            self.assertIn(b'  workflow_call:\n', after)

    def test_historical_provisioner_retains_exact_immutable_reference_bytes(self):
        path = 'Tests/Production/prepare_data.py'
        historical = subprocess.check_output(['git', '-C', str(ROOT), 'show', 'b8a2b610:' + path])
        self.assertEqual((ROOT / path).read_bytes(), historical)

    def test_hosted_execution_retains_local_hardware_and_incomplete_status(self):
        manifest = load(ROOT / 'Docs/Production/Phase6Closeout.json')
        self.assertFalse(manifest['phase6_complete'])
        self.assertFalse(manifest['software_complete'])
        self.assertEqual(manifest['policy']['automated_windows_execution'], ['github-actions', 'local-vm'])
        self.assertEqual(manifest['policy']['local_only_acceptance'], ['performance', 'hands-on', 'controller'])
        self.assertTrue(manifest['policy']['budgets_unchanged'])
        self.assertTrue(manifest['policy']['physical_controller_required_for_phase6_complete'])


if __name__ == '__main__':
    unittest.main()
