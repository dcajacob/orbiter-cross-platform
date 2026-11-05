import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import inputs
class Inputs(unittest.TestCase):
    def test_both_full_original_parents(self):
        for case in inputs.settings()['cases']:
            body,expected=inputs.scenario(case);self.assertEqual(len(expected),6);self.assertEqual(hashlib.sha256(body).hexdigest(),case['sha256_lf'])
    def test_coherently_retagged_parent_is_rejected(self):
        case=copy.deepcopy(inputs.settings()['cases'][0]);case['sha256_lf']=hashlib.sha256(b'changed').hexdigest()
        with self.assertRaisesRegex(ValueError,'original Git blob'):inputs.scenario(case)
    def test_pause_tick_cannot_silently_move(self):
        real=inputs.settings();changed=copy.deepcopy(real);changed['cases'][0]['pause_tick']+=1
        with patch.object(inputs.json,'loads',return_value=changed):
            with self.assertRaisesRegex(ValueError,'pause ticks changed'):inputs.settings()
    def test_legacy_start_paused_extra_step_is_not_enabled(self):
        fixture=(inputs.HERE.parent/'Fixtures/Orbiter.cfg').read_text();actual=inputs.configuration(fixture)
        self.assertIn('StartPaused = FALSE',actual);self.assertNotIn('StartPaused = TRUE',actual)
        for key in ('PropStages =','PropStage0 =','PropSubsampling ='):self.assertNotIn(key,actual)
class PhysicalClocks(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/'clocks.json'
        config=inputs.settings();profiles={}
        for offset,name in enumerate(('Debug-automatic','Debug-sse2','Release-automatic','Release-sse2')):
            entries={}
            for case in config['cases']:
                body,expected=inputs.scenario(case);tick=case['pause_tick']+offset;seconds=0.0
                for _ in range(tick):seconds+=config['fixed_step']
                date=next(row.split()[2] for row in body.decode('cp1252').splitlines() if row.strip().startswith('Date MJD '))
                entries[case['id']]=dict(scenario=case['scenario'],sha256_lf=case['sha256_lf'],pause_tick=tick,paused_seconds=format(seconds,'.17g'),paused_mjd=format(float(date)+seconds/86400,'.17g'),native_verification_sha256='a'*64)
            profiles[name]=entries
        self.value=dict(schema=1,protocol='original-stock-docked-physical-clock-inputs-v1',native_runtime_source='693ce8cfb44617889d3a7218281d769a3f29cfd6',original_application_source=config['application_source'],independent_native_matrix_sha256='b'*64,profiles=profiles)
    def write(self):self.path.write_text(json.dumps(self.value))
    def read(self):self.write();return inputs.physical_clocks(self.path,'Release','sse2')
    def test_selects_exact_profile_and_preserves_original_parents(self):
        for profile,entries in self.value['profiles'].items():
            self.write();configuration,math_profile=profile.split('-');actual=inputs.physical_clocks(self.path,configuration,math_profile)
            self.assertEqual(actual['physical_clock_input_sha256'],inputs.sha(self.path))
            self.assertEqual(actual['paused_frames'],8);self.assertEqual(actual['repetitions'],2)
            for case in actual['cases']:
                self.assertEqual(case['pause_tick'],entries[case['id']]['pause_tick'])
                self.assertEqual(case['native_clock_request'],entries[case['id']]);inputs.scenario(case)
    def test_tick_seconds_association_is_exact(self):
        self.value['profiles']['Debug-automatic']['docked_ISS']['pause_tick']+=1
        with self.assertRaisesRegex(ValueError,'tick/seconds'):self.read()
    def test_epoch_association_is_exact(self):
        self.value['profiles']['Release-sse2']['docked_ISS']['paused_mjd']='51982'
        with self.assertRaisesRegex(ValueError,'tick/epoch'):self.read()
    def test_changed_original_parent_is_rejected(self):
        self.value['profiles']['Release-sse2']['docked_ISS']['sha256_lf']='c'*64
        with self.assertRaisesRegex(ValueError,'original parent'):self.read()
    def test_omitted_case_is_rejected(self):
        del self.value['profiles']['Debug-sse2']['docked_ISS_demo']
        with self.assertRaisesRegex(ValueError,'Both complete'):self.read()
    def test_omitted_profile_is_rejected(self):
        del self.value['profiles']['Debug-automatic']
        with self.assertRaisesRegex(ValueError,'All four'):self.read()
    def test_retagged_native_producer_is_rejected(self):
        self.value['native_runtime_source']='0'*40
        with self.assertRaisesRegex(ValueError,'source producer'):self.read()
if __name__=='__main__':unittest.main()
