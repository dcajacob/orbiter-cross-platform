"""Published provisioning replay rejects altered hashes, versions, source identities and unsafe ZIPs."""
import copy
import io
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile
import verify_published_original_pool as replay


class PublishedOriginalPoolTests(unittest.TestCase):
    def test_signed_release_requires_unique_strong_hash_and_exact_size(self):
        self.assertEqual(replay.release_hashes('Suite: resolute\nSHA256:\n '+'a'*64+' 123 main/binary-amd64/Packages\nSHA512:\n'),{'main/binary-amd64/Packages':('a'*64,123)})
        for text in ('SHA256:\n short 123 index\n','SHA256:\n '+'a'*64+' 123 index\n '+'a'*64+' 123 index\n','SHA256:\nSHA256:\n','SHA256:\n'):
            with self.assertRaises(ValueError):replay.release_hashes(text)

    def test_every_planned_blob_needs_signed_index_hash_size_and_original_version(self):
        fields=dict(Filename='pool/main/a/a/a_1_amd64.deb',SHA256='b'*64,Size='22',Package='a',Version='1');row=['uri','mirror','a_1_amd64.deb','22','b'*64];found=set()
        replay.planned_package(fields,{fields['Filename']:row},{'a':'1'},found);self.assertEqual(found,{fields['Filename']})
        for key,value in [('SHA256','c'*64),('Size','23'),('Version','2'),('Package','b')]:
            changed=dict(fields);changed[key]=value
            with self.assertRaises(ValueError):replay.planned_package(changed,{fields['Filename']:row},{'a':'1'},set())

    def test_provisioning_zip_cannot_escape_root_collide_or_use_alias(self):
        for names in (['../escape'],['/escape'],['a','A'],['a\\b'],['a:b']):
            with tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'input.zip'
                with zipfile.ZipFile(path,'w') as z:
                    for name in names:z.writestr(name,b'original')
                with self.assertRaises(ValueError):replay.restore_zip(Path(temp)/'root',path)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'input.zip';item=zipfile.ZipInfo('alias');item.external_attr=(stat.S_IFLNK|0o777)<<16
            with zipfile.ZipFile(path,'w') as z:z.writestr(item,b'target')
            with self.assertRaises(ValueError):replay.restore_zip(Path(temp)/'root',path)

    def test_existing_different_provisioning_file_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'root';(root/'out').mkdir(parents=True);existing=root/'out/original';existing.write_bytes(b'changed');path=Path(temp)/'input.zip'
            with zipfile.ZipFile(path,'w') as z:z.writestr('original',b'original')
            with self.assertRaises(ValueError):replay.restore_zip(root,path)
            self.assertEqual(existing.read_bytes(),b'changed')

    def test_original_network_and_capture_controls_are_preserved(self):
        root=Path(__file__).resolve().parents[3]/'Tests/Production/Closeout'
        expected=(root/'prepare_hosted_class_original_pool_network.sh').read_text().replace('Tests/Production/Closeout/prepare_hosted_class_official_pool_preflight.sh|Tests/Production/Closeout/prepare_hosted_class_rejection_userspace.sh','Tests/Production/Closeout/prepare_hosted_class_rejections_official_pool.sh')
        self.assertEqual((root/'prepare_hosted_class_rejections_official_pool_network.sh').read_text(),expected)
        script=(root/'prepare_hosted_class_rejections_official_pool.sh').read_text()
        self.assertIn('bash Tests/Production/Closeout/prepare_original_packages_from_official_pool.sh\nbash Tests/Production/Closeout/prepare_hosted_class_rejections_sdk.sh',script)
        self.assertIn('sha256sum --check',script)
