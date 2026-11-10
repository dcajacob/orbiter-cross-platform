"""Source-declared non-bootstrap helpers and delegated descriptors cannot bypass SDK checks."""
import ast
import copy
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from contracts import ROOT
import restore_rejection_sdk_header as sdk


class RejectionSdkTopologyTests(unittest.TestCase):
    def fixture(self,temp,name='Atlantis.so'):
        root=Path(temp);build=root/'out/phase6-hosted-native/Debug-sse2/engine';path=build/'NativeModules/Vessel'/name;path.parent.mkdir(parents=True)
        path.write_bytes(b'\x7fELF\x00original delegated entry\x00');provider=build/'liborbiter_native_atlantis.so';provider.write_bytes(b'\x7fELF\x00'+b'a'*64+b':Debug\x00')
        runtime={provider.relative_to(root).as_posix():sdk.sha(provider)}
        entry=dict(defined=['OrbiterNativeQuery'],undefined=[sdk.ATLANTIS_QUERIES.get(name,'unknown')],needed=[provider.name],commands={})
        owner=dict(defined=list(sdk.ATLANTIS_QUERIES.values()),undefined=[],needed=[],commands={})
        return root,build,path,provider,runtime,entry,owner

    def test_strict_original_token_scanner_and_header_substitutions_are_byte_identical(self):
        before=subprocess.check_output(['git','-C',str(ROOT),'show','0d3ab0f68cb6adb8c82746ba310fdf28c48c2d59:Tests/Production/Closeout/restore_rejection_sdk_header.py'],text=True)
        after=(ROOT/'Tests/Production/Closeout/restore_rejection_sdk_header.py').read_text()
        def functions(body):return {n.name:ast.get_source_segment(body,n) for n in ast.parse(body).body if isinstance(n,ast.FunctionDef)}
        old=functions(before);new=functions(after)
        for name in ('binary_sdk_base','header_bytes','source_guards'):self.assertEqual(old[name],new[name])
        self.assertEqual(len(sdk.topology_source_guards(ROOT)),5)

    def test_each_original_atlantis_entry_must_import_its_exact_owner_and_owner_token(self):
        for name in sdk.ATLANTIS_QUERIES:
            with tempfile.TemporaryDirectory() as temp:
                root,build,path,provider,runtime,entry,owner=self.fixture(temp,name)
                with patch.object(sdk,'topology_source_guards',return_value={}),patch.object(sdk,'elf_metadata',side_effect=[entry,owner]):
                    role,actual,base=sdk.resolve_sdk_owner(path,build,'Debug',runtime,root,'a'*64)
                self.assertEqual(role['query'],sdk.ATLANTIS_QUERIES[name]);self.assertEqual(actual,provider);self.assertEqual(base,'a'*64)
                self.assertEqual(role['kind'],'original-Atlantis-delegated-bootstrap')

    def test_wrong_import_export_dependency_provider_bytes_or_provider_sdk_still_fail(self):
        for change in ('query','undefined','needed','provider-export','provider-digest','provider-sdk'):
            with tempfile.TemporaryDirectory() as temp:
                root,build,path,provider,runtime,entry,owner=self.fixture(temp)
                if change=='query':entry['defined']=[]
                elif change=='undefined':entry['undefined']=['OrbiterNativeAtlantisTankQuery']
                elif change=='needed':entry['needed']=[]
                elif change=='provider-export':owner['defined'].pop()
                elif change=='provider-digest':provider.write_bytes(provider.read_bytes()+b'changed')
                else:
                    provider.write_bytes(b'\x7fELF\x00'+b'b'*64+b':Debug\x00');runtime[provider.relative_to(root).as_posix()]=sdk.sha(provider)
                with patch.object(sdk,'topology_source_guards',return_value={}),patch.object(sdk,'elf_metadata',side_effect=[entry,owner]):
                    with self.assertRaises(ValueError):sdk.resolve_sdk_owner(path,build,'Debug',runtime,root,'a'*64)

    def test_only_exact_original_shared_lua_helper_without_bootstrap_exports_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            root,build,path,provider,runtime,entry,owner=self.fixture(temp);helper=build/'NativeModules/Plugin/LuaInterpreter.so';helper.parent.mkdir();helper.write_bytes(b'\x7fELF\x00original Lua helper\x00')
            for defined,allowed in (([],True),(['OrbiterNativeQuery'],False),(['OrbiterNativeOtherQuery'],False)):
                with patch.object(sdk,'topology_source_guards',return_value={}),patch.object(sdk,'elf_metadata',return_value=dict(defined=defined,undefined=[],needed=[],commands={})):
                    if allowed:
                        role,actual,base=sdk.resolve_sdk_owner(helper,build,'Debug',runtime,root,'a'*64);self.assertIsNone(actual);self.assertIsNone(base);self.assertEqual(role['kind'],'original-shared-Lua-helper-without-bootstrap-descriptor')
                    else:
                        with self.assertRaises(ValueError):sdk.resolve_sdk_owner(helper,build,'Debug',runtime,root,'a'*64)

    def test_ambiguous_or_wrong_configuration_tokens_and_unknown_modules_cannot_use_topology(self):
        with tempfile.TemporaryDirectory() as temp:
            root,build,path,provider,runtime,entry,owner=self.fixture(temp)
            for body in (b'prefix'+b'a'*64+b':Debug\x00',b'\x00'+b'a'*64+b':Release\x00',b'\x00'+b'a'*64+b':Debug\x00'+b'b'*64+b':Debug\x00'):
                path.write_bytes(b'\x7fELF'+body)
                with self.assertRaises(ValueError):sdk.resolve_sdk_owner(path,build,'Debug',runtime,root,'a'*64)
            unknown=build/'NativeModules/Vessel/HST.so';unknown.write_bytes(b'\x7fELF\x00missing original SDK\x00')
            with patch.object(sdk,'topology_source_guards',return_value={}),patch.object(sdk,'elf_metadata',return_value=entry):
                with self.assertRaises(ValueError):sdk.resolve_sdk_owner(unknown,build,'Debug',runtime,root,'a'*64)

    def test_prepared_source_topology_replacement_preserves_every_original_capture_step(self):
        original=(ROOT/'.github/workflows/phase6-native-class-rejections-sdk.yml').read_text()
        replacement=(ROOT/'.github/workflows/phase6-native-class-rejections-sdk-topology.yml').read_text()
        self.assertEqual(replacement.replace('Phase 6 Original Rejection Controls Source Declared SDK Topology','Phase 6 Original Rejection Controls SDK Header Restoration',1).replace('qualification/native-class-rejections-v4','qualification/native-class-rejections-v3',1),original)
