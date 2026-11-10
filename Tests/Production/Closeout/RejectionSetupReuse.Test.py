"""A completed package-only prerequisite cannot hide its failed four-profile history."""
import copy
from pathlib import Path
import tempfile
import unittest
from contracts import ROOT,load
import verify_rejection_setup_receipt as setup


class RejectionSetupReuseTests(unittest.TestCase):
    def fixture(self):return load(ROOT/'Tests/Production/Closeout/rejection-setup-v2-api.fixture.json')

    def test_only_the_exact_real_failed_run_and_successful_readiness_job_are_accepted(self):
        api=self.fixture();setup.validate_api(api)
        self.assertEqual(sum(j['conclusion']=='failure' for j in api['jobs']),4)
        self.assertEqual(sum(j['conclusion']=='success' for j in api['jobs']),1)

    def test_changed_source_runner_archive_failure_or_partial_history_cannot_supply_setup(self):
        mutations=(lambda a:a['run'].update(head_sha='0'*40),lambda a:a['run'].update(conclusion='success'),
            lambda a:a['run']['repository'].update(private=True),lambda a:a['artifact'].update(digest='sha256:'+'0'*64),
            lambda a:a['artifact'].update(expired=True),lambda a:a['jobs'].pop(),
            lambda a:a['jobs'][0].update(conclusion='failure'),lambda a:a['jobs'][1].update(conclusion='success'),
            lambda a:a['jobs'][1].update(labels=['ubuntu-latest']),lambda a:a['jobs'][1].update(run_attempt=2))
        for mutate in mutations:
            api=self.fixture();mutate(api)
            with self.assertRaises(ValueError):setup.validate_api(api)

    def test_coherent_api_cannot_accept_changed_actual_archive_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'receipt.zip';path.write_bytes(b'not the original complete package receipt')
            with self.assertRaises(ValueError):setup.inspect(self.fixture(),path)
