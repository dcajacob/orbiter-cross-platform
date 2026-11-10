"""Omitted SDK repair must keep the exact original compiled ABI and rejection acceptance."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from contracts import ROOT,atomic_json
import restore_rejection_sdk_header as sdk
import hosted_class_rejections_sdk as adapter


class RejectionSdkRestorationTests(unittest.TestCase):
    def fixture(self,temp):
        root=Path(temp)/'workspace';profile='Debug-automatic';build=root/'out/phase6-hosted-native'/profile/'engine';build.mkdir(parents=True)
        for name in sdk.SOURCES:
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
        cache=build/'CMakeCache.txt';cache.write_text('CMAKE_BUILD_TYPE:STRING=Debug\nORBITER_BUILD_NATIVE_COCKPIT:BOOL=ON\nORBITER_MATH_FORCE_SSE2:BOOL=OFF\n')
        paths=[cache]
        for name in ('liborbiter_production_boundary.so','NativeModules/Vessel/HST.so','NativeModules/Graphics/OGLClient.so'):
            p=build/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'\x7fELF\x00'+b'a'*64+b':Debug\x00');paths.append(p)
        record=dict(status='built',source_base=sdk.COMPILED,owning_sources_unchanged=True,instrumentation='address,undefined',configuration='Debug',math_profile='automatic',runtime_files_sha256={p.relative_to(root).as_posix():sdk.sha(p) for p in paths})
        manifest=build.parent/'build.json';atomic_json(manifest,record)
        guards={str(root/n):sdk.sha(root/n) for n in sdk.SOURCES}
        return root,build,manifest,record,guards

    def test_sdk_template_abi_cmake_and_loader_bytes_match_the_original_compiled_source(self):
        self.assertEqual(len(sdk.source_guards(ROOT)),4)

    def test_actual_binary_identity_must_be_unique_correct_configuration_and_elf(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'module.so';base=b'b'*64
            p.write_bytes(b'\x7fELF\x00'+b'x'*(1024*1024-24)+b'\x00'+base+b':Release\x00')
            self.assertEqual(sdk.binary_sdk_base(p,'Release'),'b'*64)
            for body,configuration in ((b'not-ELF\x00'+base+b':Debug\x00','Debug'),(b'\x7fELF\x00'+base+b':Release\x00','Debug'),
                (b'\x7fELF\x00'+base+b':Debug\x00'+b'c'*64+b':Debug\x00','Debug'),(b'\x7fELF\x00prefix'+base+b':Debug\x00','Debug')):
                p.write_bytes(body)
                with self.assertRaises(ValueError):sdk.binary_sdk_base(p,configuration)

    def test_generated_header_has_only_the_two_original_configure_file_substitutions(self):
        template=(ROOT/sdk.SOURCES[0]).read_bytes();expected=template.replace(b'@ORBITER_NATIVE_BUILD_BASE@',b'a'*64).replace(b'#cmakedefine01 ORBITER_BUILD_NATIVE_COCKPIT',b'#define ORBITER_BUILD_NATIVE_COCKPIT 1')
        self.assertEqual(sdk.header_bytes(template,'a'*64,'ON'),expected)
        for base,cockpit in (('a'*63,'ON'),('G'*64,'ON'),('a'*64,'OFF')):
            with self.assertRaises(ValueError):sdk.header_bytes(template,base,cockpit)

    def test_exact_missing_header_is_declared_reconstructed_without_changing_any_old_input(self):
        with tempfile.TemporaryDirectory() as temp:
            root,build,manifest,record,guards=self.fixture(temp);before={p:p.read_bytes() for p in (root).rglob('*') if p.is_file()};out=root/'out/restored.json'
            with patch.object(sdk,'source_guards',return_value=guards):report=sdk.restore('Debug-automatic',manifest,out,root)
            self.assertTrue(all(p.read_bytes()==v for p,v in before.items()));self.assertEqual(len(report['binary_SDK_build_bases']),3)
            self.assertFalse(report['header_was_in_original_retained_archive']);self.assertFalse(report['compiled_runtime_rebuilt']);self.assertFalse(report['original_capture_or_audit_relabelled']);self.assertFalse(report['phase6_complete'])
            header=Path(report['header']);self.assertEqual(sdk.sha(header),report['header_sha256']);header.write_bytes(b'wrong existing SDK\n')
            with patch.object(sdk,'source_guards',return_value=guards):
                with self.assertRaises(ValueError):sdk.restore('Debug-automatic',manifest,root/'out/another.json',root)
            self.assertEqual(header.read_bytes(),b'wrong existing SDK\n')

    def test_missing_changed_cross_profile_or_disagreeing_compiled_identity_cannot_supply_a_header(self):
        for mutate in ('changed-module','disagreeing-sdk','wrong-source','wrong-cockpit'):
            with tempfile.TemporaryDirectory() as temp:
                root,build,manifest,record,guards=self.fixture(temp);module=build/'NativeModules/Vessel/HST.so'
                if mutate=='changed-module':module.write_bytes(module.read_bytes()+b'changed')
                elif mutate=='disagreeing-sdk':
                    module.write_bytes(b'\x7fELF\x00'+b'b'*64+b':Debug\x00');record['runtime_files_sha256'][module.relative_to(root).as_posix()]=sdk.sha(module)
                elif mutate=='wrong-source':record['source_base']='0'*40
                else:
                    cache=build/'CMakeCache.txt';cache.write_text(cache.read_text().replace('COCKPIT:BOOL=ON','COCKPIT:BOOL=OFF'));record['runtime_files_sha256'][cache.relative_to(root).as_posix()]=sdk.sha(cache)
                atomic_json(manifest,record)
                with patch.object(sdk,'source_guards',return_value=guards):
                    with self.assertRaises(ValueError):sdk.restore('Debug-automatic',manifest,root/'out/restored.json',root)
                self.assertFalse((build/'native-sdk/OrbiterNativeBuild.h').exists())

    def test_adapter_keeps_every_original_test_guard_timeout_and_signed_network_setting(self):
        before=adapter.ORIGINAL_PREPARED();after=adapter.prepared_body()
        self.assertEqual(after.replace(adapter.INSERT+adapter.ANCHOR,adapter.ANCHOR,1),before)
        bootstrap=(ROOT/'Tests/Production/Closeout/prepare_hosted_class_rejections_sdk.sh').read_text()
        self.assertEqual(bootstrap.replace('hosted_class_rejections_sdk.py','hosted_class_rejections.py'),(ROOT/'Tests/Production/Closeout/prepare_hosted_class_rejections.sh').read_text())
        network=(ROOT/'Tests/Production/Closeout/prepare_hosted_class_rejections_network_v3.sh').read_text()
        self.assertEqual(network.replace('prepare_hosted_class_rejections_sdk.sh|','prepare_hosted_class_rejections.sh|'),(ROOT/'Tests/Production/Closeout/prepare_hosted_class_rejections_network_v2.sh').read_text())
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'out/hosted-native-class-rejections/Debug-automatic';out.mkdir(parents=True);header=root/'out/header.h';header.write_bytes(b'exact SDK\n')
            atomic_json(out/'original-SDK-header-restoration.json',dict(profile='Debug-automatic',compiled_source=sdk.COMPILED,header=str(header),header_sha256=sdk.sha(header),header_was_in_original_retained_archive=False,original_sources_sha256={},original_binary_and_cache_sha256={}))
            atomic_json(out/'original-fixture-SDK.json',dict(files_sha256={str(header):sdk.sha(header)}))
            with patch.object(adapter,'ORIGINAL_PACK',return_value='preserved') as pack:
                self.assertEqual(adapter.pack_with_sdk(root,set(),out/'raw-original-inputs.tar.gz',out/'raw-index.json'),'preserved')
                self.assertIn(header,pack.call_args.args[1]);self.assertIn(Path(adapter.sdk.__file__),pack.call_args.args[1])

    def test_replacement_workflow_preserves_all_four_original_capture_steps_and_only_reuses_setup(self):
        old=(ROOT/'.github/workflows/phase6-native-class-rejections.yml').read_text()
        new=(ROOT/'.github/workflows/phase6-native-class-rejections-sdk.yml').read_text()
        normalized=new.split('  capture:',1)[1].replace('prepare_hosted_class_rejections_network_v3.sh Tests/Production/Closeout/prepare_hosted_class_rejections_sdk.sh','prepare_hosted_class_rejections_network_v2.sh Tests/Production/Closeout/prepare_hosted_class_rejections.sh')
        self.assertEqual(normalized,old.split('  capture:',1)[1])
        self.assertIn("branches: ['qualification/native-class-rejections-v3']",new)
        self.assertIn('verify_rejection_setup_receipt.py',new)
        self.assertNotIn('docker run',new.split('  capture:',1)[0])
        self.assertIn('actual_package_count', (ROOT/'Tests/Production/Closeout/verify_rejection_setup_receipt.py').read_text())
