#!/usr/bin/env python3
"""Guest jobs cannot be relaunched or reuse an unrelated closed receipt."""
from pathlib import Path
import base64
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from contracts import atomic_json,load
import local_vm


class GuestTests(unittest.TestCase):
    def nonce_fixture(self,root):
        script=root/'worker.py';script.write_text('print("owned child")\n');job=root/'job.json'
        with patch.object(local_vm.subprocess,'check_output',return_value='test-uuid\n'),patch.object(local_vm,'virsh',return_value={'pid':123}):
            local_vm.submit('win11','test-uuid','C:/Python/python.exe',script,'Z:/share/worker.py',[],job,True)
        body=load(job);transport=body['transport']
        record=dict(protocol=transport['protocol'],nonce=transport['nonce'],request_sha256=transport['request_sha256'],
            wrapper_sha256=transport['wrapper_sha256'],actual_wrapper_pid=123,platform='win32',
            target_script=body['guest_script'],target_sha256=body['script_sha256'],target_argv=body['argv'],
            actual_target_pid=456,actual_target_returncode=0,actual_target_start_identity=dict(kind='windows-process-creation-filetime',value=789),
            status='completed-nonce-bound-actual-child-exit',target_source_unchanged=True,
            **{'out-data':base64.b64encode(b'owned child\n').decode(),'err-data':''})
        return job,body,record

    def test_unrelated_agent_terminal_never_completes_nonce_job(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);job,body,record=self.nonce_fixture(root);terminal=root/'terminal.json'
            stale=dict(exited=True,exitcode=1,**{'out-data':base64.b64encode(b'unrelated old job').decode()})
            with patch.object(local_vm.subprocess,'check_output',return_value='test-uuid\n'),patch.object(local_vm,'virsh',return_value=stale):
                pending=local_vm.poll(job,terminal);self.assertFalse(pending['exited']);self.assertFalse(terminal.exists())
                self.assertEqual(len(list(root.glob('terminal.json.unmatched-agent-*.json'))),1)
                atomic_json(Path(body['transport']['result_local']),record)
                actual=local_vm.poll(job,terminal)
                self.assertTrue(actual['exited']);self.assertEqual(actual['exitcode'],0);self.assertFalse(actual['agent_receipt_matched'])
                self.assertEqual(actual['agent_terminal'],stale);self.assertEqual(actual['transport_receipt']['actual_target_pid'],456)

    def test_nonce_source_pid_and_start_identity_mutations_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            unused,job,record=self.nonce_fixture(Path(temp))
            for field,value in [('nonce','another-job'),('target_sha256','0'*64),('actual_wrapper_pid',999),('platform','linux')]:
                bad=copy.deepcopy(record);bad[field]=value
                with self.assertRaises(ValueError):local_vm.validate_nonce_receipt(job,bad)
            bad=copy.deepcopy(record);bad['actual_target_start_identity']['value']=0
            with self.assertRaises(ValueError):local_vm.validate_nonce_receipt(job,bad)

    def test_nonce_transport_failure_is_terminal_and_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);unused,job,record=self.nonce_fixture(root)
            record.update(status='failed',error='Target source changed before spawn',actual_target_pid=None,actual_target_returncode=None)
            atomic_json(Path(job['transport']['result_local']),record)
            actual=local_vm.nonce_terminal(job,dict(exited=False),root/'terminal.json')
            self.assertTrue(actual['exited']);self.assertEqual(actual['exitcode'],1)
            self.assertEqual(actual['terminal_basis'],'nonce-bound-transport-failure')

    def test_actual_wrapper_child_exit_and_changed_source_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);worker=root/'worker.py';marker=root/'executed.txt'
            worker.write_text('from pathlib import Path\nimport sys\nPath('+repr(str(marker))+').write_text("ran")\nprint("owned child")\nsys.exit(7)\n')
            wrapper=Path(local_vm.__file__).parent/'LocalVM/guest_job_v2.py'
            for mode in ('actual-child','changed-source'):
                output=root/(mode+'-result.json');request=root/(mode+'.json')
                cfg=dict(nonce=mode,python=sys.executable,script=str(worker),script_sha256=local_vm.sha(worker) if mode=='actual-child' else '0'*64,
                    argv=['-B',str(worker)],wrapper_sha256=local_vm.sha(wrapper),expected_platform=sys.platform,cwd=str(root),result=str(output))
                atomic_json(request,cfg);completed=subprocess.run([sys.executable,'-B',str(wrapper),str(request)],capture_output=True,text=True)
                result=load(output)
                if mode=='actual-child':
                    self.assertEqual(completed.returncode,0);self.assertEqual(result['actual_target_returncode'],7)
                    self.assertGreater(result['actual_target_start_identity']['value'],0);self.assertTrue(marker.exists());marker.unlink()
                else:
                    self.assertNotEqual(completed.returncode,0);self.assertEqual(result['status'],'failed')
                    self.assertIsNone(result['actual_target_pid']);self.assertFalse(marker.exists())

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
