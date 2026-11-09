"""Small real ZIP/capacity fixtures for hosted physical audit entry; no runtime credit."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
from contracts import ROOT

sys.path.insert(0,str(ROOT/'Tests/Production/CurrentWindows/Hosted'))
import audit_current_phase_cli as cli

spec=importlib.util.spec_from_file_location('physical_cli_closed_api_fixture',ROOT/'Tests/Production/Closeout/SourceCompleteClosedPhase.Test.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


class CurrentPhysicalCliTests(unittest.TestCase):
    def archive(self,root):
        archive=root/'actual-api.zip'
        with zipfile.ZipFile(archive,'w') as source:source.writestr('fixture-only.json',json.dumps({'runtime_credit':False}))
        api=fixture.SourceCompleteClosedPhaseTests().api()
        api['artifact'].update(size_in_bytes=archive.stat().st_size,digest='sha256:'+cli.sha(archive))
        return api,archive

    def test_entry_decodes_only_exact_completed_api_archive_bytes_into_a_fresh_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);api,archive=self.archive(root);target=root/'decoded'
            members=cli.decode_current(api,archive,target,('Debug','automatic','stock'))
            self.assertEqual(members,{'fixture-only.json':cli.sha(target/'fixture-only.json')})
            with self.assertRaises(ValueError):cli.decode_current(api,archive,target,('Debug','automatic','stock'))
            changed=copy.deepcopy(api);changed['jobs'][0]['conclusion']='failure'
            with self.assertRaises(ValueError):cli.decode_current(changed,archive,root/'failed-API',('Debug','automatic','stock'))
            self.assertFalse((root/'failed-API').exists())
            with archive.open('ab') as stream:stream.write(b'changed source archive')
            with self.assertRaises(ValueError):cli.decode_current(api,archive,root/'changed-archive',('Debug','automatic','stock'))
            self.assertFalse((root/'changed-archive').exists())

    def test_entry_does_not_consume_the_unchanged_eight_gibibyte_reserve(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);api,archive=self.archive(root);target=root/'decoded'
            with patch.object(cli.shutil,'disk_usage',return_value=SimpleNamespace(free=8*1024**3)):
                with self.assertRaisesRegex(ValueError,'capacity reserve'):
                    cli.decode_current(api,archive,target,('Debug','automatic','stock'))
            self.assertFalse(target.exists())

    def test_unproven_scalar_api_is_rejected_before_touching_any_kernel_or_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);api=root/'wrong-api.json'
            api.write_text(json.dumps(dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),
                run={'id':-1},artifact={},jobs=[])))
            with self.assertRaises(ValueError):cli.scalar_binding(api,root/'absent.zip',None,'a'*40)
            self.assertEqual({p.name for p in root.iterdir()},{'wrong-api.json'})


if __name__=='__main__':unittest.main()
