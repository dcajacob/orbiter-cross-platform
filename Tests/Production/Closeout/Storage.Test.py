#!/usr/bin/env python3
"""Archive restoration must reject corruption, missing members and unsafe paths."""
import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile
from contracts import sha
from storage import safe_name, verify_archive


class StorageTests(unittest.TestCase):
    def test_full_restore_and_damaged_hash_or_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);archive=root/'evidence.zip'
            with zipfile.ZipFile(archive,'x') as z:
                z.writestr('case/state.csv',b'tick,state\n0,1\n')
                z.writestr('case/frame.rgba',bytes(range(32)))
            with zipfile.ZipFile(archive) as z:
                inventory={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
            result=verify_archive(archive,sha(archive),inventory,root)
            self.assertEqual(len(result['restored_files']),2)
            self.assertEqual(list(root.iterdir()),[archive])
            for digest,members in [('0'*64,inventory),(sha(archive),{}),
                                   (sha(archive),dict(inventory,**{'case/state.csv':'0'*64}))]:
                with self.subTest(digest=digest,members=members),self.assertRaises(ValueError):
                    verify_archive(archive,digest,members,root)
            self.assertEqual(list(root.iterdir()),[archive])

    def test_unsafe_names_duplicates_and_symlinks(self):
        for name in ('../escape','/absolute','C:/root','case\\file','case/../escape','case//alias',''):
            with self.subTest(name=name),self.assertRaises(ValueError):safe_name(name)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);archive=root/'link.zip'
            item=zipfile.ZipInfo('link');item.external_attr=0o120777<<16
            with zipfile.ZipFile(archive,'x') as z:z.writestr(item,b'target')
            with self.assertRaisesRegex(ValueError,'regular'):
                verify_archive(archive,sha(archive),{'link':hashlib.sha256(b'target').hexdigest()},root)


if __name__=='__main__':unittest.main()
