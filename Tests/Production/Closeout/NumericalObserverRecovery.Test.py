from pathlib import Path
from unittest import TestCase
import copy
import numerical_observer_equivalence as n
import hosted_numerical_observer as hosted


class NumericalObserverRecovery(TestCase):
    def receipt(self):
        return dict(terminal=True,cancelled=False,actual_returncode=0,actual_collector_pid=37,owned_process_identities=[dict(pid=37,start_ticks=123,argv=['/actual/simulator','--frames','960'])])

    def test_actual_completed_process_identity_is_required(self):
        value=self.receipt();self.assertEqual(n.actual_process(value,['/actual/simulator','--frames','960'])['pid'],37)
        for key,v in [('terminal',False),('cancelled',True),('actual_returncode',1)]:
            broken=copy.deepcopy(value);broken[key]=v
            with self.assertRaises(ValueError):n.actual_process(broken,['/actual/simulator','--frames','960'])

    def test_requested_argv_cannot_replace_actual_observed_argv(self):
        with self.assertRaises(ValueError):n.actual_process(self.receipt(),['/forged/simulator'])

    def test_start_identity_and_unique_collector_are_required(self):
        for mutate in ('start','duplicate','missing'):
            value=self.receipt()
            if mutate=='start':value['owned_process_identities'][0]['start_ticks']=0
            if mutate=='duplicate':value['owned_process_identities']*=2
            if mutate=='missing':value['owned_process_identities']=[]
            with self.assertRaises(ValueError):n.actual_process(value,['/actual/simulator','--frames','960'])

    def test_complete_original_runtime_preflight_is_preserved(self):
        body=hosted.prepared_body();compile(body,'prepared','exec')
        for text in ['package_inventory(actual)==inventory','compositor_preflight','prepare_native_data.py','prepare_hosted_data.py','verify_native_runtime','verify_restored','stage_configuration','original-save-baseline-and-observer-off-on']:self.assertIn(text,body)
        self.assertNotIn("run('all-38-stock-writers-twice'",body)
        self.assertIn('actual_processes=3',body)

    def test_original_source_locks_and_saved_input_are_not_refreshed(self):
        self.assertEqual(n.sha(n.INPUT),n.INPUT_SHA)
        self.assertEqual(n.load(n.ROOT/'Tests/Production/Math/Reference/ReloadAtan2/provenance.json')['saved_input_sha256'],n.INPUT_SHA)
        import subprocess
        for name in n.ORIGINAL:self.assertEqual((n.ROOT/name).read_bytes(),subprocess.check_output(['git','show',n.COMPILED+':'+name]))
