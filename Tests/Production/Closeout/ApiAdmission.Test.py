"""The corrected API variant is opt-in and edits only its private script copy."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'GeneralApiCorrection'))
import admission as api


class ApiAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.cfg=api.startup_contract.settings()
        self.case=dict(sha256_lf=self.cfg['scenario_sha256_lf'],ships=self.cfg['vessels'])
        self.selected=dict(body=dict(status='qualified-general-api-correction-v2',policy=self.cfg))
    def test_absent_qualification_keeps_original_policy(self):
        self.assertIsNone(api.policy(self.cfg['scenario'],self.case,None))
    def test_another_scene_does_not_receive_api_exit_policy(self):
        self.assertIsNone(api.policy('2024 Edition/Spotlights.scn',self.case,self.selected))
    def test_changed_scene_or_roster_is_rejected(self):
        for field,value in [('sha256_lf','0'*64),('ships',{})]:
            case=copy.deepcopy(self.case);case[field]=value
            with self.assertRaises(ValueError):api.policy(self.cfg['scenario'],case,self.selected)
    def test_only_private_script_bytes_change(self):
        with tempfile.TemporaryDirectory(prefix='phase6-api-private-assets-') as temp:
            source=Path(temp)/'original';target=Path(temp)/'private'
            for name,body in {api.ORIGINAL:(api.ROOT/api.ORIGINAL).read_bytes(),
                              'Config/unchanged.cfg':b'unchanged stock input\n',
                              'Scenarios/Tests/GeneralApiTest.scn':(api.ROOT/'Scenarios/Tests/GeneralApiTest.scn').read_bytes()}.items():
                path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
            proof=api.stage_assets(source,target)
            changed=[name for name,pair in proof['files_sha256'].items() if pair['original']!=pair['variant']]
            self.assertEqual(changed,[api.ORIGINAL]);self.assertEqual((source/api.ORIGINAL).read_bytes(),(api.ROOT/api.ORIGINAL).read_bytes())
