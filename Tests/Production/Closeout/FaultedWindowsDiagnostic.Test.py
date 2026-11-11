from pathlib import Path
import tempfile,unittest
from unittest.mock import Mock
from capture_failed_normal_windows import compiler_batch,read_compiler_environment,stage_observer,original_configuration,observed_scene_run


class FaultedWindowsDiagnostic(unittest.TestCase):
    def test_quoted_compiler_path_runs_through_a_real_batch_file(self):
        vc=r'C:\Program Files\Microsoft Visual Studio\18\Enterprise\Common7\Tools\VsDevCmd.bat'
        body=compiler_batch(vc)
        self.assertEqual(body,'@call "'+vc+'" -arch=x64 -host_arch=x64 >nul\n@if errorlevel 1 exit /b %errorlevel%\n@set\n')
        reader=Mock(return_value='PATH=compiler\n')
        self.assertEqual(read_compiler_environment('cmd.exe',Path('work/compiler-environment.bat'),reader),'PATH=compiler\n')
        reader.assert_called_once_with(['cmd.exe','/d','/c',str(Path('work/compiler-environment.bat'))],text=True)

    def test_observer_copy_preserves_hardlinked_pristine_sdk(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);sdk=root/'pristine.dll';stage=root/'staged.dll';observer=root/'observer.dll'
            sdk.write_bytes(b'original SDK');stage.hardlink_to(sdk);observer.write_bytes(b'exact original passive observer')
            stage_observer(observer,stage)
            self.assertEqual(sdk.read_bytes(),b'original SDK')
            self.assertEqual(stage.read_bytes(),observer.read_bytes())
            self.assertNotEqual(sdk.stat().st_ino,stage.stat().st_ino)

    def test_original_configuration_isolated_from_generic_inventory_module(self):
        import sys,types
        fake=types.ModuleType('inventory')
        with unittest.mock.patch.dict(sys.modules,{'inventory':fake}):
            body=original_configuration()
        for field in ('PropStages','PropStage0','PropSubsampling'):
            self.assertNotIn(field,body)
        self.assertIn('AtmosphericWind = FALSE',body)
        self.assertIn('InfobarMode = 0',body)

    def test_absent_sdk_placeholder_is_created_as_a_separate_observer_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'observer.dll';source.write_bytes(b'exact observer')
            target=root/'stage/Modules/Plugin/ProductionCockpitDriver.dll'
            stage_observer(source,target)
            self.assertEqual(target.read_bytes(),source.read_bytes())
            self.assertNotEqual(source.stat().st_ino,target.stat().st_ino)

    def test_actual_process_receipt_distinguishes_launch_from_staging(self):
        import sys,json
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp)
            with (directory/'console.txt').open('w') as console:
                result=observed_scene_run([sys.executable,'-c',"print('actual disposable child')"],cwd=directory,stdout=console,check=True,timeout=5)
            record=json.loads((directory/'process-receipt.json').read_text())
            self.assertEqual(result.returncode,0)
            self.assertGreater(record['actual_pid'],0)
            self.assertEqual(record['actual_returncode'],0)
            self.assertFalse(record['timed_out'])
            self.assertEqual((directory/'console.txt').read_text().strip(),'actual disposable child')
