import copy,hashlib,json,unittest
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
if __name__=='__main__':unittest.main()
