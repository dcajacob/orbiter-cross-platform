"""Slow package transfer may extend setup time without changing any original qualification check."""
import ast
from pathlib import Path
import subprocess
import unittest
from contracts import ROOT
import hosted_class_rejection_userspace as setup
import hosted_class_rejections as capture


class RejectionProvisioningDeadlineTests(unittest.TestCase):
    def test_preflight_only_changes_the_one_original_provisioning_deadline(self):
        original=setup.ORIGINAL.read_text();actual=setup.prepared_body();ast.parse(actual)
        self.assertEqual(actual.replace('def run(label,argv,timeout=3600):','def run(label,argv,timeout=1200):'),original)
        self.assertIn('verify_inventory(expected_body,actual)',actual);self.assertIn('SNAPSHOT',actual)

    def test_capture_extends_only_the_exact_original_package_install_stage(self):
        source=subprocess.check_output(['git','-C',str(ROOT),'show',setup.ORIGINAL_SOURCE+':Tests/Production/Closeout/hosted_class_rejections.py'],text=True)
        node=next(v for v in ast.parse(source).body if isinstance(v,ast.FunctionDef) and v.name=='prepared_body')
        namespace=dict(capture.__dict__);exec(compile(ast.Module(body=[node],type_ignores=[]),'immutable-original-prepared-body','exec'),namespace)
        old=namespace['prepared_body']();actual=capture.prepared_body()
        before="        run('restore-original-system-packages',['apt-get','install','-y','--no-install-recommends',*[name+'='+version for name,version in inventory.items()]],1200)"
        after=before.replace(']],1200)',']],3600)')
        self.assertEqual(actual.replace(after,before),old)
        self.assertIn("run('all-original-forty-five-normal-host-rejection-controls',argv,14400",actual)
        self.assertIn("'--runtime-role','normal','--jobs','1'",actual)

    def test_new_bootstrap_keeps_every_original_signed_archive_and_inventory_guard(self):
        old=(ROOT/'Tests/Production/Closeout/prepare_hosted_class_rejections_network.sh').read_text()
        new=(ROOT/'Tests/Production/Closeout/prepare_hosted_class_rejections_network_v2.sh').read_text()
        self.assertEqual(new.replace('prepare_hosted_class_rejection_userspace.sh','prepare_hosted_class_userspace.sh'),old)
        original=(ROOT/'Tests/Production/Closeout/prepare_hosted_class_userspace.sh').read_text()
        actual=(ROOT/'Tests/Production/Closeout/prepare_hosted_class_rejection_userspace.sh').read_text()
        self.assertEqual(actual.replace('hosted_class_rejection_userspace.py','hosted_class_userspace.py'),original)
