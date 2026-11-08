"""Reject incomplete startup exits without weakening ordinary scene acceptance."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'GeneralApiCorrection'))
import startup_contract as api


class GeneralApiStartupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='phase6-api-exit-control-')
        self.addCleanup(self.temp.cleanup);self.out=Path(self.temp.name)
        self.script=self.out/'test.lua';self.scenario=self.out/'test.scn';self.save=self.out/'saved.scn'
        body,unused=api.corrected((api.ROOT/api.ORIGINAL).read_bytes(),(api.ROOT/api.EARTH).read_bytes(),'v2')
        self.script.write_bytes(body);self.scenario.write_bytes((api.ROOT/'Scenarios/Tests/GeneralApiTest.scn').read_bytes())
        self.save.write_bytes(api.SAVE_SENTINEL)
        self.write('graphics-lifecycle.json',dict(rendered_frames=0,successful_presents=0,context_deleted=True))
        self.write('numerics.json',dict(math='amd-6121d02-fma3'))
        (self.out/'console.log').write_text('\n'.join(api.EXPECTED_EVENTS)+'\n')
        self.state=dict(tick='0',frame='0',seconds='0',mjd='51982.5292925579',object='GL-01',
                        **{'class':'DeltaGlider'},rx='1',ry='1',rz='1',vx='1',vy='1',vz='1',
                        wx='0',wy='0',wz='0',mass='18673.7',fuel='7133.7',focus='GL-01')
        self.states([self.state])

    def write(self,name,value): (self.out/name).write_text(json.dumps(value)+'\n')
    def states(self,values):
        with (self.out/'flight-state.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(self.state));writer.writeheader();writer.writerows(values)
    def inspect(self,profile='Debug-automatic',code=0):
        return api.inspect_native(self.out,profile,code,self.script,self.scenario,self.save)
    def reject(self):
        with self.assertRaises((ValueError,OSError,KeyError)): self.inspect()

    def test_complete_startup_all_four_profiles(self):
        for config in ('Debug','Release'):
            for mode in ('automatic','sse2'):
                self.write('numerics.json',dict(math='amd-6121d02-'+('sse2' if mode=='sse2' else 'fma3')))
                self.assertTrue(self.inspect(config+'-'+mode)['existing_save_preserved'])
    def test_original_script_is_rejected(self): self.script.write_bytes((api.ROOT/api.ORIGINAL).read_bytes());self.reject()
    def test_changed_scenario_is_rejected(self): self.scenario.write_bytes(b'changed');self.reject()
    def test_missing_vessel_is_rejected(self): self.states([]);self.reject()
    def test_duplicate_vessel_is_rejected(self): self.states([self.state,self.state]);self.reject()
    def test_substituted_class_is_rejected(self): self.state['class']='Atlantis';self.states([self.state]);self.reject()
    def test_extra_tick_is_rejected(self): self.state['tick']='1';self.states([self.state]);self.reject()
    def test_wrong_math_is_rejected(self): self.write('numerics.json',dict(math='amd-6121d02-sse2'));self.reject()
    def test_unclean_context_is_rejected(self):
        self.write('graphics-lifecycle.json',dict(rendered_frames=0,successful_presents=0,context_deleted=False));self.reject()
    def test_rendered_frame_is_rejected(self):
        self.write('graphics-lifecycle.json',dict(rendered_frames=1,successful_presents=1,context_deleted=True));self.reject()
    def test_missing_assertion_is_rejected(self): (self.out/'console.log').write_text('\n'.join(api.EXPECTED_EVENTS[2:]));self.reject()
    def test_sanitizer_error_is_rejected(self):
        with (self.out/'console.log').open('a') as stream: stream.write('ERROR: LeakSanitizer: retained object\n')
        self.reject()
    def test_nonzero_exit_is_rejected(self):
        with self.assertRaises(ValueError): self.inspect(code=1)
    def test_overwritten_save_is_rejected(self): self.save.write_bytes(b'overwritten');self.reject()
    def test_nonfinite_state_is_rejected(self): self.state['vx']='nan';self.states([self.state]);self.reject()
    def test_unknown_profile_is_rejected(self):
        with self.assertRaises(ValueError): self.inspect(profile='Debug-other')
    def test_empty_windows_roster_is_rejected(self):
        (self.out/'api-startup-objects.csv').write_text('phase,name,class\n')
        with self.assertRaises(ValueError): api.inspect_windows_roster(self.out,True)
    def test_disabled_windows_observer_is_empty(self):
        (self.out/'api-startup-objects.csv').write_text('phase,name,class\n')
        (self.out/'api-startup-events.csv').write_text('phase,event_object\n')
        self.assertEqual(api.inspect_windows_roster(self.out,False),[])
