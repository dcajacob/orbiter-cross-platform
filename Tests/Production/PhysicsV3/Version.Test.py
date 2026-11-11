import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PhysicsV3 import source

class PhysicsVersion(unittest.TestCase):
    def fixture(self, root):
        manifest = json.loads((source.HERE / 'version.json').read_text())
        names = set(source.INPUTS) | set(source.expected_sources()) | set(manifest['original_guard_files_sha256_lf'])
        names |= {'Tests/Production/PhysicsV2/version.json', source.OLD_BUILDER, 'Tests/Production/PhysicsV3/.gitattributes'}
        for name in names:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((source.ROOT / name).read_bytes())

    def isolated_git(self, root):
        original = source.git
        def git(*args, **kwargs):
            if kwargs.get('root') == root and args[0] in ('diff', 'ls-files'):
                return b''
            return original(*args, **kwargs)
        return git

    def test_exact_new_source_and_separate_builder(self):
        for name, expected in source.expected_sources().items():
            self.assertEqual(source.normalized((source.ROOT / name).read_bytes()), expected)
        self.assertEqual((source.HERE / '.gitattributes').read_text(), 'correction.patch text eol=lf\n')
        self.assertNotIn(b'\r', (source.HERE / 'correction.patch').read_bytes())

    def test_extra_physics_change_cannot_be_hidden_by_manifest_rehash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            with patch.object(source, 'git', side_effect=self.isolated_git(root)):
                source.validate_current(root)
                target = root / source.TARGET
                target.write_bytes(target.read_bytes() + b'\nint undeclared_physics_change = 1;\n')
                path = root / 'Tests/Production/PhysicsV3/version.json'
                manifest = json.loads(path.read_text())
                manifest['corrected_source_sha256_lf'] = source.digest(target.read_bytes())
                path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, 'Unreviewed physics'):
                    source.validate_current(root)

    def test_original_acceptance_reader_cannot_be_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            target = root / 'Tests/Production/StockScenarios/run.py'
            target.write_bytes(target.read_bytes() + b'\n# changed acceptance\n')
            with patch.object(source, 'git', side_effect=self.isolated_git(root)):
                with self.assertRaisesRegex(ValueError, 'Original guard or acceptance'):
                    source.validate_current(root)

    def test_v2_manifest_cannot_be_relabelled(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            target = root / 'Tests/Production/PhysicsV2/version.json'
            target.write_bytes(target.read_bytes() + b'\n')
            with patch.object(source, 'git', side_effect=self.isolated_git(root)):
                with self.assertRaisesRegex(ValueError, 'Original v2 version/builder'):
                    source.validate_current(root)

if __name__ == '__main__':
    unittest.main()
