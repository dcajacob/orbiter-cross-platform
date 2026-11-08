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
                # The optional retained-SDK route forces the same complete build
                # and records XML from the same CTest invocation. The original
                # application/client/cockpit/control bodies remain byte exact.
                rebuild=b"if: steps.rebuild.outputs.needed == 'true'"
                self.assertEqual(expected.count(rebuild),1)
                expected=expected.replace(rebuild,rebuild+b' || inputs.retain_stock_sdk')
                ctest=b'ctest --test-dir out/runtime-rebuild --output-on-failure '
                self.assertEqual(expected.count(ctest),1)
                expected=expected.replace(ctest,ctest+b'--output-junit "$pwd/out/runtime-rebuild/runtime-ctest.xml" ')
                retention=b'''      - name: Retain the exact current application and SDK for full stock qualification
        if: inputs.retain_stock_sdk
        run: python -B Tests/Production/CurrentWindows/retain_hosted_sdk.py --configuration ${{ matrix.configuration }} --output out/current-windows-sdk
      - name: Upload the current SDK without granting stock qualification
        uses: actions/upload-artifact@v7
        if: inputs.retain_stock_sdk && always()
        with:
          name: current-windows-sdk-${{ matrix.configuration }}
          retention-days: 14
          compression-level: 0
          path: |
            out/current-windows-sdk/*.json
            out/current-windows-sdk/*.xml
            out/current-windows-sdk/*.log
            out/current-windows-sdk/runtime.zip
            out/current-windows-sdk/tested-driver-variants/**
'''
                self.assertEqual(after.count(retention),1)
                after=after.replace(retention,b'',1)
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
