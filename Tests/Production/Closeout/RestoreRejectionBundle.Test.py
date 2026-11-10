"""A published original rejection can only be replayed with exact safe bytes, aliases and original audit values."""
import copy
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import rejection_input_bundle as bundle
import restore_rejection_input_bundle as restored


class RestoreRejectionBundleTests(unittest.TestCase):
    def fixture(self,temp):
        root=Path(temp)/'workspace';folder=root/'out/native-class-rejections/fixture/control';folder.mkdir(parents=True)
        source=root/'Tests/owned.py';source.parent.mkdir();source.write_bytes(b'original immutable source\n')
        a=folder/'second';a.write_bytes(b'original second\n');b=folder/'first';b.write_bytes(b'original first\n')
        shared=root/'out/assets/shared';shared.parent.mkdir();shared.write_bytes(b'original shared bytes\n')
        os.link(shared,folder/'hard-copy');(folder/'alias').symlink_to('first')
        order=[p.name for p in folder.iterdir() if p.is_file()]
        archive=Path(temp)/'original.tar.gz';index=bundle.pack(root,{source,shared,*folder.iterdir()},archive,Path(temp)/'index.json')
        shutil.rmtree(root/'out/native-class-rejections');shutil.rmtree(root/'out/assets')
        return root,folder,archive,index,{'out/native-class-rejections/fixture/control':order},source

    def test_actual_byte_hardlink_alias_and_recorded_file_membership_are_restored_without_source_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root,folder,archive,index,orders,source=self.fixture(temp);before=source.read_bytes()
            with patch.object(restored.shutil,'disk_usage',return_value=SimpleNamespace(free=100*1024**3)):
                result=restored.restore(root,archive,index,root/'out/rejection-independent/fixture/objects',orders)
            self.assertEqual(source.read_bytes(),before);self.assertEqual(set(p.name for p in folder.iterdir() if p.is_file()),set(next(iter(orders.values()))))
            self.assertEqual(result['original_flat_file_record_orders'],orders)
            self.assertEqual(result['actual_restored_file_enumeration_orders'][next(iter(orders))],[p.name for p in folder.iterdir() if p.is_file()])
            self.assertTrue((folder/'hard-copy').samefile(root/'out/assets/shared'));self.assertEqual(os.readlink(folder/'alias'),'first')
            self.assertFalse(result['original_audit_or_capture_relabelled']);self.assertEqual(result['new_simulator_processes'],0)
            self.assertTrue(result['independent_original_rejection_audit_still_required']);self.assertFalse(result['phase6_complete'])
            self.assertFalse((root/'out/rejection-independent/fixture/objects').exists())

    def test_changed_owning_source_is_never_overwritten_to_fit_a_capture(self):
        with tempfile.TemporaryDirectory() as temp:
            root,folder,archive,index,orders,source=self.fixture(temp);source.write_bytes(b'new actual owning source\n')
            with self.assertRaises(ValueError):restored.restore(root,archive,index,root/'out/rejection-independent/fixture/objects',orders)
            self.assertEqual(source.read_bytes(),b'new actual owning source\n');self.assertFalse(folder.exists())

    def test_wrong_root_digest_missing_guard_privilege_and_recorded_file_scope_are_rejected(self):
        for change in (lambda i:i.update(source_root='/another-root'),lambda i:i.update(archive_sha256='0'*64),
                       lambda i:i.update(missing_guarded_paths=['lost']),lambda i:next(iter(i['files'].values())).update(mode=0o4755)):
            with tempfile.TemporaryDirectory() as temp:
                root,folder,archive,index,orders,source=self.fixture(temp);value=copy.deepcopy(index);change(value)
                with self.assertRaises(ValueError):restored.restore(root,archive,value,root/'out/rejection-independent/fixture/objects',orders)
        with tempfile.TemporaryDirectory() as temp:
            root,folder,archive,index,orders,source=self.fixture(temp)
            orders[next(iter(orders))].append('unrecorded')
            with patch.object(restored.shutil,'disk_usage',return_value=SimpleNamespace(free=100*1024**3)):
                with self.assertRaises(ValueError):restored.restore(root,archive,index,root/'out/rejection-independent/fixture/objects',orders)

    def test_capacity_reserve_and_parent_alias_guards_remain_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root,folder,archive,index,orders,source=self.fixture(temp)
            with patch.object(restored.shutil,'disk_usage',return_value=SimpleNamespace(free=8*1024**3-1)):
                with self.assertRaises(ValueError):restored.restore(root,archive,index,root/'out/rejection-independent/fixture/objects',orders)
            self.assertFalse(folder.exists())
            parent=root/'out/native-class-rejections';parent.symlink_to(root/'out/assets')
            with self.assertRaises(ValueError):restored.checked_path(root,'out/native-class-rejections/anything')


    def test_original_field_types_values_lists_and_non_file_table_order_cannot_change(self):
        old=dict(status='audited-negative-loader-and-class-controls-only',controls={'HST-metadata-0':dict(actual_exitcode=1,
            lifecycle=dict(rendered_frames=0,successful_presents=0,context_deleted=True),files_sha256={'console.log':'a'*64,'invocation.json':'b'*64})},
            families=['HST'],sanitizer_suppressions=False)
        fresh=copy.deepcopy(old);fresh['controls']['HST-metadata-0']['files_sha256']={'invocation.json':'b'*64,'console.log':'a'*64}
        before=copy.deepcopy((old,fresh));result=restored.compare_original_audit(old,fresh,['HST-metadata-0'])
        self.assertEqual((old,fresh),before);self.assertEqual(len(result['only_file_hash_table_key_order_differences']),1)
        self.assertFalse(result['original_raw_audit_or_capture_normalized']);self.assertFalse(result['acceptance_values_or_tolerances_changed'])
        for mutate in (lambda r:r['controls']['HST-metadata-0'].update(actual_exitcode=0),
                       lambda r:r['controls']['HST-metadata-0']['lifecycle'].update(rendered_frames=False),
                       lambda r:r['controls']['HST-metadata-0']['files_sha256'].update({'console.log':'0'*64}),
                       lambda r:r['controls']['HST-metadata-0']['files_sha256'].pop('console.log'),
                       lambda r:r.update(families=['HST','other']),
                       lambda r:r['controls']['HST-metadata-0'].update(lifecycle=dict(context_deleted=True,rendered_frames=0,successful_presents=0))):
            changed=copy.deepcopy(fresh);mutate(changed)
            with self.assertRaises(ValueError):restored.compare_original_audit(old,changed,['HST-metadata-0'])
