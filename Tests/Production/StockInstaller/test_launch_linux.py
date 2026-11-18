"""Verify isolation and persistence for installations shared by Linux users."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "Utils/StockDataInstaller"))
from launch_linux import personal_profile


class SharedInstallTest(unittest.TestCase):
    def test_separate_accounts_keep_their_settings_and_share_the_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            install = root / "Shared install"
            seed = install / "user/Orbiter.cfg"
            seed.parent.mkdir(parents=True)
            seed.write_text("original")
            (install / "Launchpad profile.json").write_text(json.dumps({
                "mode": "native", "executable": "runtime/orbiter-production",
                "config": "user/Orbiter.cfg", "saves": "user/Scenarios",
            }))
            for account in ("a", "b"):
                home = root / account
                with patch.dict(os.environ, HOME=str(home), XDG_DATA_HOME="relative"):
                    path = personal_profile(install)
                    profile = json.loads(path.read_text())
                    config = Path(profile["config"])
                    self.assertTrue(path.is_relative_to(home / ".local/share"))
                    self.assertTrue(Path(profile["saves"]).is_dir())
                    self.assertEqual(profile["executable"], str(install / "runtime/orbiter-production"))
                    self.assertEqual(config.read_text(), "original")
                    config.write_text(account)
                    self.assertEqual(personal_profile(install), path)
                    self.assertEqual(config.read_text(), account)
            self.assertEqual(seed.read_text(), "original")
