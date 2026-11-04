"""Prove the derived diagnostics preserve every original physics/object byte."""
import copy,hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import common
class Inputs(unittest.TestCase):
    def test_only_declared_HUD_fields_change(self):
        c=common.settings();raw=(common.ROOT/c['parent_scenario']).read_bytes().replace(b'\r\n',b'\n')
        body,names=common.scenario(c['cases'][0]);restored=body.replace(b'BEGIN_HUD\n  TYPE Orbit\nEND_HUD',b'BEGIN_HUD\n  TYPE Surface\nEND_HUD',1)
        restored=restored.replace(b'  HUDMode 1\n',b'',1).replace(b'  HUDMode 2\n',b'',1)
        self.assertEqual(restored,raw);self.assertEqual(len(names),8)
    def test_only_declared_focus_changes(self):
        c=common.settings();raw=(common.ROOT/c['parent_scenario']).read_bytes().replace(b'\r\n',b'\n');body,names=common.scenario(c['cases'][1])
        self.assertEqual(body.replace(b'  Ship PB-01\n',b'  Ship GL-01\n',1),raw);self.assertEqual(len(names),8)
    def test_coherently_retagged_original_parent_is_rejected(self):
        actual=common.settings();changed=copy.deepcopy(actual);changed['parent_sha256_lf']=hashlib.sha256(b'different stock input').hexdigest()
        original_load=common.json.loads
        with patch.object(common.json,'loads',side_effect=lambda value:changed):
            with self.assertRaisesRegex(ValueError,'coherently retagged'):common.settings()
if __name__=='__main__':unittest.main()
