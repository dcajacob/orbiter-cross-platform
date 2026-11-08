"""Retained current SDKs must keep their immutable producer and complete test receipts."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from contracts import ROOT

spec=importlib.util.spec_from_file_location('hosted_current_sdk',ROOT/'Tests/Production/CurrentWindows/retain_hosted_sdk.py')
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)


class HostedWindowsSdkTests(unittest.TestCase):
    def test_every_registered_process_must_pass_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'tests.xml';inventory={'tests':[{'name':'original-one'},{'name':'original-two'}]}
            good='<testsuite><testcase name="original-one"/><testcase name="original-two"/></testsuite>'
            path.write_text(good);self.assertEqual(reader.unit_result(inventory,path)['executed_processes'],2)
            for value in (good.replace('original-two','original-one'),good.replace('<testcase name="original-two"/>',''),
                          good.replace('original-two','substitute'),good.replace('/>','><skipped/></testcase>',1),
                          good.replace('/>','><failure/></testcase>',1),good.replace('/>','><error/></testcase>',1)):
                path.write_text(value)
                with self.assertRaises(ValueError):reader.unit_result(inventory,path)
            path.write_text(good)
            with self.assertRaises(ValueError):reader.unit_result({'tests':[]},path)

    def fixture(self,root):
        names=('Orbiter.exe','Orbitersdk/lib/Orbiter.lib','Orbitersdk/lib/Orbitersdk.lib',
               'Orbitersdk/include/Orbitersdk.h','Modules/Plugin/OGLClient.dll')
        for name in names:
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'explicit-control-fixture-only')
        manifest={'source_commit':'a'*40,'files':{name:reader.sha(root/name) for name in names if 'OGLClient' not in name}}
        (root/'test-runtime.json').write_text(json.dumps(manifest));return manifest

    def test_retained_runtime_rejects_changed_producer_sdk_and_missing_renderer(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);manifest=self.fixture(root)
            files=reader.runtime_files(root,'a'*40);self.assertIn('Modules/Plugin/OGLClient.dll',files)
            with self.assertRaises(ValueError):reader.runtime_files(root,'b'*40)
            path=root/'Orbitersdk/include/Orbitersdk.h';path.write_bytes(b'changed-sdk')
            with self.assertRaises(ValueError):reader.runtime_files(root,'a'*40)
            self.fixture(root);(root/'Modules/Plugin/OGLClient.dll').unlink()
            with self.assertRaises(ValueError):reader.runtime_files(root,'a'*40)

    def test_original_sdk_members_cannot_escape(self):
        for name in ('../outside','/absolute','C:/outside','folder\\outside','folder/./alias','folder//alias','.'):
            with self.assertRaises(ValueError):reader.safe(name)

    def test_only_the_client_test_driver_can_differ_from_the_pristine_sdk(self):
        for changed in ('Modules/Plugin/ProductionBehaviorDriver.dll','Orbiter.exe'):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);tested=root/'tested';tested.mkdir();sdk=self.fixture(tested)
                driver=tested/'Modules/Plugin/ProductionBehaviorDriver.dll';driver.write_bytes(b'original-test-driver')
                sdk['files'][driver.relative_to(tested).as_posix()]=reader.sha(driver)
                (tested/'test-runtime.json').write_text(json.dumps(sdk))
                archive=root/'sdk.zip'
                with zipfile.ZipFile(archive,'w') as z:
                    for name in [*sdk['files'],'test-runtime.json']:z.write(tested/name,name)
                (tested/changed).write_bytes(b'client-rebuild')
                if changed=='Orbiter.exe':
                    with self.assertRaises(ValueError):reader.prepare_runtime(archive,tested,root/'retained',root/'variants','a'*40)
                else:
                    result=reader.prepare_runtime(archive,tested,root/'retained',root/'variants','a'*40)
                    self.assertEqual(set(result),{changed})
                    self.assertEqual((root/'retained'/changed).read_bytes(),b'original-test-driver')
                    self.assertEqual((root/'variants/ProductionBehaviorDriver.dll').read_bytes(),b'client-rebuild')
                    reader.runtime_files(root/'retained','a'*40)

    def test_full_stock_preparation_reuses_every_existing_windows_check(self):
        workflow=(ROOT/'.github/workflows/phase6-current-windows-sdk.yml').read_text()
        self.assertIn('uses: ./.github/workflows/production-client.yml',workflow)
        self.assertIn('retain_stock_sdk: true',workflow)
        self.assertIn('runs-on: ubuntu-24.04',workflow)
        self.assertNotIn('windows-2022',workflow)


if __name__=='__main__':unittest.main()
