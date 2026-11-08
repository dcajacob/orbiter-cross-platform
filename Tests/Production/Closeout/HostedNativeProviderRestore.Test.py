"""Immutable dependency restoration must reject mixed sources or lost archive closure."""
import copy
import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
import restore_hosted_native_providers as reader


class HostedNativeProviderRestoreTests(unittest.TestCase):
    def record(self):
        return dict(repository=dict(owner='dcajacob',repo='orbiter-cross-platform'),
            run=dict(id=reader.RUN,head_sha=reader.PRODUCER,head_branch='qualification/native-providers-retry',
                     path='.github/workflows/phase6-native-providers.yml',run_attempt=1,status='completed',conclusion='success'),
            artifact=dict(id=reader.ARTIFACT,name='native-stock-runtime-providers',expired=False,size_in_bytes=reader.SIZE,
                          digest='sha256:'+reader.DIGEST,workflow_run=dict(id=reader.RUN,head_sha=reader.PRODUCER)),
            jobs=[dict(id=128876988468,run_id=reader.RUN,head_sha=reader.PRODUCER,status='completed',conclusion='success',labels=['ubuntu-24.04'])])

    def test_complete_successful_producer_is_pinned(self):
        reader.validate_api(self.record())
        for change in (lambda r:r['run'].update(head_sha='f'*40),lambda r:r['run'].update(run_attempt=2),
                       lambda r:r['artifact'].update(digest='sha256:'+'0'*64),lambda r:r['artifact'].update(size_in_bytes=1),
                       lambda r:r['artifact'].update(expired=True),lambda r:r['jobs'][0].update(conclusion='failure'),
                       lambda r:r['jobs'][0].update(labels=['self-hosted']),lambda r:r['jobs'].append(copy.deepcopy(r['jobs'][0]))):
            record=self.record();change(record)
            with self.assertRaises(ValueError):reader.validate_api(record)

    def archive(self,root,entries):
        path=root/'provider.tar.gz';expected={};body=b'fixture dependency bytes'
        with tarfile.open(path,'w:gz') as target:
            for name,kind,link in entries:
                info=tarfile.TarInfo(name);info.mode=0o755
                if kind=='file':info.size=len(body);target.addfile(info,io.BytesIO(body))
                else:
                    info.type=tarfile.SYMTYPE if kind=='symlink' else tarfile.LNKTYPE;info.linkname=link;target.addfile(info)
                expected[name]=dict(sha256=hashlib.sha256(body).hexdigest(),symlink=link if kind=='symlink' else None)
        return path,expected

    def test_actual_files_symlinks_and_forward_hardlinks_keep_exact_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);prefix=reader.PREFIX
            archive,expected=self.archive(root,[(prefix+'/hard','hardlink',prefix+'/lib.so.1'),
                (prefix+'/lib.so.1','file',None),(prefix+'/lib.so','symlink','lib.so.1')])
            base=reader.restore_tree(archive,expected,root)
            self.assertEqual((base/'lib.so').resolve(),base/'lib.so.1')
            self.assertEqual((base/'hard').stat().st_ino,(base/'lib.so.1').stat().st_ino)
            with self.assertRaises(ValueError):reader.restore_tree(archive,expected,root)

    def test_incomplete_or_modified_archive_is_rejected(self):
        for mutation in ('missing','extra','hash','target'):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);prefix=reader.PREFIX
                archive,expected=self.archive(root,[(prefix+'/lib.so.1','file',None),(prefix+'/lib.so','symlink','lib.so.1')])
                if mutation=='missing':expected.pop(prefix+'/lib.so')
                elif mutation=='extra':expected[prefix+'/absent']=dict(sha256='f'*64,symlink=None)
                elif mutation=='hash':expected[prefix+'/lib.so.1']['sha256']='f'*64
                else:expected[prefix+'/lib.so']['symlink']='another.so'
                with self.assertRaises(ValueError):reader.restore_tree(archive,expected,root)

    def test_original_package_versions_cannot_be_replaced_by_unversioned_inputs(self):
        from capture_hosted_native_writer import package_inventory
        self.assertEqual(package_inventory('libfixture:amd64=1:2.0~rc1-3ubuntu1\npython3=3.14.0-1\n'),
                         {'libfixture:amd64':'1:2.0~rc1-3ubuntu1','python3':'3.14.0-1'})
        for body in ('','python3','python3=3.14\npython3=3.15','package=1;command','--option=1','package=$(command)'):
            with self.assertRaises(ValueError):package_inventory(body)

    def test_native_asset_preparation_supplies_a_private_original_configuration(self):
        from capture_hosted_native_writer import stage_configuration
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'original.cfg';source.write_bytes(b'; Original configuration fixture\n')
            source.chmod(0o444);assets=root/'assets';assets.mkdir()
            checksum=reader.sha(source);result=stage_configuration(source,assets)
            self.assertEqual(result['sha256'],checksum);self.assertEqual(reader.sha(assets/'Orbiter.cfg'),checksum)
            self.assertNotEqual(source.stat().st_ino,(assets/'Orbiter.cfg').stat().st_ino)
            (assets/'Orbiter.cfg').chmod(0o644);(assets/'Orbiter.cfg').write_bytes(b'Private runtime input\n')
            self.assertEqual(reader.sha(source),checksum)
            with self.assertRaises(ValueError):stage_configuration(source,assets)
            (assets/'Orbiter.cfg').unlink();(assets/'Orbiter.cfg').symlink_to(root/'absent')
            with self.assertRaises(ValueError):stage_configuration(source,assets)

    def test_member_paths_and_links_cannot_escape_or_alias(self):
        for name,kind,link in (('../outside','file',None),(reader.PREFIX+'/lib','symlink','../../outside'),
                (reader.PREFIX+'/lib','symlink','/etc/passwd'),(reader.PREFIX+'/hard','hardlink','../outside')):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);archive,expected=self.archive(root,[(name,kind,link)])
                with self.assertRaises(ValueError):reader.restore_tree(archive,expected,root)
                self.assertFalse((root/'outside').exists())


if __name__=='__main__':unittest.main()
