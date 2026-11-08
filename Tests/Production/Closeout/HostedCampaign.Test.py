#!/usr/bin/env python3
"""The hosted launcher preserves every existing reusable qualification job."""
from pathlib import Path
import subprocess
import unittest

from contracts import ROOT, load


class HostedCampaignTests(unittest.TestCase):
    def test_reused_workflow_jobs_and_test_commands_are_byte_identical(self):
        for name in ('production-client.yml', 'matched-clock-remaining-stock-full.yml', 'native-production-client.yml'):
            path = '.github/workflows/' + name
            before = subprocess.check_output(['git', '-C', str(ROOT), 'show', 'bee7e1c1:' + path])
            after = (ROOT / path).read_bytes()
            self.assertEqual(before.split(b'\njobs:\n', 1)[1], after.split(b'\njobs:\n', 1)[1], name)
            self.assertIn(b'  workflow_call:\n', after)

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
