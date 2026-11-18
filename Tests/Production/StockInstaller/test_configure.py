"""Check first-run Windows renderer selection without starting a desktop."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "Utils/StockDataInstaller"))
from installer import configure


class WindowsConfigurationTest(unittest.TestCase):
    def test_fresh_and_existing_configurations(self):
        cases = (
            (b"", [b"OGLClient"]),
            (b"ACTIVE_MODULES\r\n  XRSound\r\nEND_MODULES\r\n", [b"XRSound", b"OGLClient"]),
            (b"ACTIVE_MODULES\n  D3D9Client\nEND_MODULES\n", [b"D3D9Client"]),
        )
        for previous, expected in cases:
            with self.subTest(previous=previous), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                runtime = root / "runtime"
                runtime.mkdir()
                config = runtime / "Orbiter.cfg"
                if previous:
                    config.write_bytes(previous)
                configure(root, runtime, True)
                configure(root, runtime, True)
                result = config.read_bytes()
                modules = result.split(b"ACTIVE_MODULES")[1].split(b"END_MODULES")[0]
                self.assertCountEqual(modules.split(), expected)
                self.assertEqual(result.count(b"ImGui_ManuscriptFontFile"), 1)


if __name__ == "__main__":
    unittest.main()
