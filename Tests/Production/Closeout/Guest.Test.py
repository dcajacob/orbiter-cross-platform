#!/usr/bin/env python3
"""Guest jobs cannot be relaunched or reuse an unrelated closed receipt."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from contracts import atomic_json,load
import local_vm


class GuestTests(unittest.TestCase):
    def test_submit_once_and_bind_retained_terminal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);script=root/'worker.py';script.write_text('pass\n');job=root/'job.json';terminal=root/'terminal.json'
            with patch.object(local_vm.subprocess,'check_output',return_value='test-uuid\n'),patch.object(local_vm,'virsh',return_value={'pid':123}) as call:
                local_vm.submit('win11','test-uuid','C:/Python/python.exe',script,'Z:/share/worker.py',['request.json'],job)
                self.assertEqual(call.call_count,1)
                with self.assertRaises(ValueError):local_vm.submit('win11','test-uuid','C:/Python/python.exe',script,'Z:/share/worker.py',[],job)
                self.assertEqual(call.call_count,1)
            with patch.object(local_vm.subprocess,'check_output',return_value='test-uuid\n'),patch.object(local_vm,'virsh',side_effect=[{'exited':False},{'exited':True,'exitcode':0}]) as call:
                self.assertFalse(local_vm.poll(job,terminal)['exited']);self.assertFalse(terminal.exists())
                self.assertEqual(local_vm.poll(job,terminal)['exitcode'],0)
                self.assertEqual(local_vm.poll(job,terminal)['exitcode'],0);self.assertEqual(call.call_count,2)
            changed=load(job);changed['pid']=999;atomic_json(job,changed)
            with self.assertRaisesRegex(ValueError,'binding'):local_vm.poll(job,terminal)

    def test_rejected_wrong_vm_and_failed_submission_retains_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);script=root/'worker.py';script.write_text('pass\n');job=root/'job.json'
            with patch.object(local_vm.subprocess,'check_output',return_value='wrong\n'),self.assertRaises(ValueError):
                local_vm.submit('win11','expected','python',script,'Z:/worker.py',[],job)
            self.assertFalse(job.exists())
            with patch.object(local_vm.subprocess,'check_output',return_value='expected\n'),patch.object(local_vm,'virsh',side_effect=RuntimeError('offline')),self.assertRaises(RuntimeError):
                local_vm.submit('win11','expected','python',script,'Z:/worker.py',[],job)
            self.assertEqual(load(job)['status'],'submission-failed')
            with self.assertRaises(ValueError):local_vm.poll(job,root/'terminal.json')


if __name__=='__main__':unittest.main()
