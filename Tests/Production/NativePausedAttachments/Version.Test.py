#!/usr/bin/env python3
"""Reject hidden source changes and preserve every previous acceptance input."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import source

class VersionControls(unittest.TestCase):
    def fixture(self,root):
        names=set(source.INPUTS)|{source.TARGET,source.OLD_BUILDER}
        names.update(source.git('ls-tree','-r','--name-only',source.BASELINE,'--','Tests/Production/PhysicsV3').decode().splitlines())
        previous=json.loads((source.ROOT/'Tests/Production/PhysicsV3/version.json').read_text())
        names.update(previous['original_guard_files_sha256_lf'])
        for name in names:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((source.ROOT/name).read_bytes())
    def isolated_git(self,root):
        original=source.git
        def git(*args,**kwargs):
            if kwargs.get('root')==root and args[0] in ('diff','ls-files'):return b''
            return original(*args,**kwargs)
        return git
    def test_exact_scoped_sources(self):
        source.validate_current()
        self.assertEqual((source.HERE/'.gitattributes').read_text(),'correction.patch text eol=lf\n')
        self.assertNotIn(b'\r',(source.HERE/'correction.patch').read_bytes())
    def test_rehashed_extra_native_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.fixture(root)
            with patch.object(source,'git',side_effect=self.isolated_git(root)):
                source.validate_current(root);target=root/source.TARGET
                target.write_bytes(target.read_bytes()+b'\nint hidden_native_change=1;\n')
                path=root/'Tests/Production/NativePausedAttachments/version.json';manifest=json.loads(path.read_text())
                manifest['corrected_source_sha256_lf']=source.digest(target.read_bytes());path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError,'Unreviewed native bootstrap'):source.validate_current(root)
    def test_previous_builder_stays_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.fixture(root);target=root/source.OLD_BUILDER;target.write_bytes(target.read_bytes()+b'\n# changed old guard\n')
            with patch.object(source,'git',side_effect=self.isolated_git(root)):
                with self.assertRaisesRegex(ValueError,'Original v3 physics version'):source.validate_current(root)
    def test_previous_acceptance_stays_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.fixture(root);target=root/'Tests/Production/StockScenarios/run.py';target.write_bytes(target.read_bytes()+b'\n# changed acceptance\n')
            with patch.object(source,'git',side_effect=self.isolated_git(root)):
                with self.assertRaisesRegex(ValueError,'Original v3 physics version'):source.validate_current(root)

if __name__=='__main__':unittest.main()
