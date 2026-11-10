"""Lossless bundling preserves logical files and original byte/type identity without qualification."""
import copy
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
import rejection_input_bundle as bundle


class RejectionBundleTests(unittest.TestCase):
    def test_all_original_file_hardlink_alias_and_missing_guard_identities_remain_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);a=root/'a';a.write_bytes(b'original repeated asset\n');b=root/'b';os.link(a,b);alias=root/'alias';alias.symlink_to('a')
            result=bundle.pack(root,{a,b,alias,root/'missing'},root/'output/raw.tar.gz',root/'output/index.json')
            self.assertEqual(set(result['files']),{'a','b','alias'});self.assertEqual(result['missing_guarded_paths'],['missing'])
            self.assertEqual(result['closure']['logical_files'],3);self.assertFalse(result['original_files_rewritten']);self.assertTrue(result['source_and_runtime_rejection_audits_still_required'])
            with tarfile.open(root/'output/raw.tar.gz') as source:
                kinds={v.name:v.type for v in source};self.assertEqual(kinds['b'],tarfile.LNKTYPE);self.assertEqual(kinds['alias'],tarfile.SYMTYPE)
            self.assertEqual(a.read_bytes(),b.read_bytes());self.assertEqual(os.readlink(alias),'a')

    def test_changed_bytes_removed_members_and_redirected_aliases_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);a=root/'a';a.write_bytes(b'original\n');b=root/'b';os.link(a,b);record=bundle.pack(root,{a,b},root/'raw.tar.gz',root/'index.json')
            for mode in ['bytes','missing','link']:
                out=root/(mode+'.tar.gz')
                with tarfile.open(root/'raw.tar.gz') as source,tarfile.open(out,'w:gz') as target:
                    for item in source:
                        if mode=='missing' and item.name=='b':continue
                        data=source.extractfile(item).read() if item.isfile() else None
                        if mode=='bytes' and item.name=='a':data=b'changed!\n';item.size=len(data)
                        if mode=='link' and item.name=='b':item.linkname='../outside'
                        target.addfile(item,io.BytesIO(data) if data is not None else None)
                with self.assertRaises(ValueError):bundle.inspect_archive(out,record['files'])

    def test_unsafe_outside_privileged_and_case_colliding_inputs_cannot_enter_a_bundle(self):
        for name in ['../outside','/absolute','a\\b','a:drive','a/../b']:
            with self.assertRaises(ValueError):bundle.safe(name)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);a=root/'a';a.write_bytes(b'actual');upper=root/'A';upper.write_bytes(b'other')
            with self.assertRaises(ValueError):bundle.inventory(root,{a,upper})
            alias=root/'alias';alias.symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):bundle.inventory(root,{alias})
            with self.assertRaises(ValueError):bundle.inventory(root,{root.parent/'outside'})
            a.chmod(0o4755)
            try:
                with self.assertRaises(ValueError):bundle.inventory(root,{a})
            finally:a.chmod(0o644)
