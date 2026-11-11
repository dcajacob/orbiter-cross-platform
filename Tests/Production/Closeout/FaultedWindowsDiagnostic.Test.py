from pathlib import Path
import tempfile,unittest
from unittest.mock import Mock
from capture_failed_normal_windows import compiler_batch,read_compiler_environment,stage_observer


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
