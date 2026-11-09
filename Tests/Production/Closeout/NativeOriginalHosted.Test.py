"""Small bootstrap/ZIP/capacity/input fixtures; no hosted physical qualification is run here."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from contracts import ROOT
import audit_native_original_cli as cli
import bootstrap_hosted_native_original_audit as bootstrap

spec=importlib.util.spec_from_file_location('native_original_hosted_raw_fixture',ROOT/'Tests/Production/Closeout/NativeAuditRetry.Test.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


class NativeOriginalHostedTests(unittest.TestCase):
    def test_entire_declared_dependency_data_asset_prefix_is_conserved_and_no_simulator_is_invoked(self):
        original=bootstrap.runtime.prepared_body();body=bootstrap.prepared_body();compile(body,'fixture-bootstrap','exec')
        restored=body.replace("output=ROOT/'out/native-original-bootstrap'/(a.profile+'-'+os.environ['NATIVE_PHASE'])", "output=ROOT/'out/hosted-native-writer'/a.profile")
        restored=restored.replace("protocol='phase6-hosted-native-original-physical-bootstrap-v1'", "protocol='phase6-hosted-native-stock-writer-runtime-v3'")
        restored=restored.replace("\n        require(os.environ.get('NATIVE_PHASE') in ('stock-writer','windows-save-reload'),'Exact retained native physical phase required')",'')
        self.assertEqual(restored[:restored.index("        require(verify_native_runtime(output/'native-runtime-dependencies.json')")],original[:original.index(bootstrap.ANCHOR)])
        self.assertNotIn('Tests/Production/RemainingStockPersistence/capture_native.py',body)
        self.assertNotIn('all-38-stock-writers-twice',body)
        self.assertIn('audit_after_bootstrap(a.profile',body)

    def test_old_network_transport_and_dependency_shell_bodies_are_preserved_under_narrow_new_audit_child(self):
        here=ROOT/'Tests/Production/Closeout'
        source=(here/'prepare_hosted_native_original_network.sh').read_text()
        source=source.replace('Tests/Production/Closeout/prepare_hosted_native_original_comparison.sh','Tests/Production/Closeout/prepare_hosted_native_retry_reload.sh')
        source=source.replace('case "${NATIVE_PHASE:-}" in stock-writer|windows-save-reload) ;; *) exit 2;; esac\noutput="out/native-original-network/$PROFILE-$NATIVE_PHASE"', 'output="out/native-runtime-network/$PROFILE"')
        self.assertEqual(source,(here/'prepare_hosted_native_retry_network.sh').read_text())
        source=(here/'prepare_hosted_native_original_comparison.sh').read_text().replace('bootstrap_hosted_native_original_audit.py','capture_hosted_native_retry_reload.py')
        self.assertEqual(source,(here/'prepare_hosted_native_retry_reload.sh').read_text())

    def test_actual_api_zip_decode_keeps_all_bytes_and_never_consumes_the_original_reserve(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);archive=root/'fixture.zip'
            with zipfile.ZipFile(archive,'w') as output:output.writestr('fixture-only.json','{"runtime_credit":false}')
            profile='Debug-automatic';pin=(*cli.physical.writers.PINS[profile][:3],archive.stat().st_size,cli.sha(archive))
            with patch.dict(cli.physical.writers.PINS,{profile:pin}):
                api=fixture.NativeAuditRetryTests().api(profile)
                with patch.object(cli.shutil,'disk_usage',return_value=SimpleNamespace(free=8*1024**3)):
                    with self.assertRaisesRegex(ValueError,'capacity reserve'):cli.decode(api,archive,root/'blocked',profile,'stock-writer')
                self.assertFalse((root/'blocked').exists())
                with patch.object(cli.shutil,'disk_usage',return_value=SimpleNamespace(free=9*1024**3)):
                    self.assertEqual(cli.decode(api,archive,root/'fresh',profile,'stock-writer'),{'fixture-only.json':cli.sha(root/'fresh/fixture-only.json')})
                    with self.assertRaises(ValueError):cli.decode(api,archive,root/'fresh',profile,'stock-writer')
                    wrong=copy.deepcopy(api);wrong['artifact']['expired']=True
                    with self.assertRaises(ValueError):cli.decode(wrong,archive,root/'expired',profile,'stock-writer')
                    archive.write_bytes(archive.read_bytes()+b'changed ZIP transport')
                    with self.assertRaises(ValueError):cli.decode(api,archive,root/'changed',profile,'stock-writer')
                self.assertFalse((root/'expired').exists());self.assertFalse((root/'changed').exists())

    def test_read_only_observation_exposure_keeps_exact_bytes_and_file_identity_without_any_relabel(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);payload=root/'out/payload';source=payload/'native-stock-writer/Debug-automatic';source.mkdir(parents=True)
            (source/'capture.json').write_text('{"fixture_only":true}');(source/'scene.csv').write_text('unchanged fixture bytes')
            with patch.object(cli,'ROOT',root),patch.object(cli.physical,'ROOT',root):
                target,receipt=cli.expose_native(payload,'Debug-automatic','stock-writer')
                self.assertEqual(target,root/'out/native-stock-writer/Debug-automatic')
                self.assertEqual((source/'capture.json').stat().st_ino,(target/'capture.json').stat().st_ino)
                self.assertFalse(receipt['original_capture_bytes_rewritten']);self.assertFalse(receipt['qualification_granted'])
                with self.assertRaises(ValueError):cli.expose_native(payload,'Debug-automatic','stock-writer')
                reload=payload/'native-stock-reload/Debug-automatic';reload.mkdir(parents=True);(reload/'capture.json').symlink_to(source/'capture.json')
                with self.assertRaises(ValueError):cli.expose_native(payload,'Debug-automatic','windows-save-reload')

    def test_captured_asset_metadata_restoration_preserves_fresh_receipts_and_requires_identical_actual_assets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);payload=root/'out/payload';captured=payload/'native-stock-assets';captured.mkdir(parents=True)
            assets=root/'out/native-stock-assets';assets.mkdir(parents=True);output=root/'out/bootstrap';output.mkdir()
            (assets/'fixture.msh').write_bytes(b'exact native asset');files={'fixture.msh':cli.sha(assets/'fixture.msh')}
            for name in ('remaining-vessels-resources.json','resources.json','cockpit-test-font.json'):
                (captured/name).write_text('{"fixture_only":"captured original"}');(assets/name).write_text('{"fixture_only":"fresh setup"}')
                files[name]=cli.sha(captured/name)
            with patch.object(cli,'ROOT',root):
                result=cli.restore_asset_metadata(payload,dict(asset_files_sha256=files),output)
                self.assertTrue(result['actual_asset_bytes_equal_captured_map']);self.assertFalse(result['captured_descriptors_relabelled'])
                self.assertEqual((output/'fresh-asset-metadata/resources.json').read_text(),'{"fixture_only":"fresh setup"}')
                self.assertEqual((assets/'resources.json').read_bytes(),(captured/'resources.json').read_bytes())
                (assets/'fixture.msh').write_bytes(b'changed actual mesh');new=root/'out/second-bootstrap';new.mkdir()
                with self.assertRaises(ValueError):cli.restore_asset_metadata(payload,dict(asset_files_sha256=files),new)


if __name__=='__main__':unittest.main()
