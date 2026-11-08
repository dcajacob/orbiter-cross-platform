"""Incomplete original cohorts cannot enter the hosted independent audit."""
import copy
import unittest
from contracts import ROOT
from audit_hosted_original_stock import writer_result,PRODUCER,PROFILES


class HostedOriginalAuditTests(unittest.TestCase):
    def report(self):
        return dict(status='passed',producer_commit=PRODUCER,protocol='remaining-stock-matched-clock-v2',
            download_manifest_sha256='a'*64,processes=304,presentations=304*960,profiles={p:{} for p in PROFILES},
            phase6_complete=False,native_admission_qualified=False)

    def test_complete_writer_result_keeps_its_original_scope(self):
        report=self.report();self.assertEqual(writer_result(report,'a'*64)['processes'],304)

    def test_missing_scope_mixed_source_and_qualification_claims_are_rejected(self):
        for key,value in (('status','failed'),('producer_commit','b'*40),('protocol','another-protocol'),
                          ('processes',303),('presentations',304*960-1),('profiles',{'Debug-automatic':{}}),
                          ('download_manifest_sha256','b'*64),('phase6_complete',True),('native_admission_qualified',True)):
            report=self.report();report[key]=value
            with self.assertRaises(ValueError):writer_result(report,'a'*64)

    def test_cloud_audit_keeps_actual_api_digest_source_and_completed_job_bindings(self):
        body=(ROOT/'.github/workflows/phase6-original-stock-audit.yml').read_text()
        for expected in ('run_id = 42515116858',PRODUCER,'digest !== artifact.digest',
                         "run.status !== 'completed'","j.conclusion !== 'success'","j.labels.includes('windows-2025')",
                         'runs-on: ubuntu-24.04','audit_hosted_original_stock.py'):
            self.assertIn(expected,body)
        self.assertNotIn('cmake --build',body)


if __name__=='__main__':unittest.main()
