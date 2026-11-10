import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import measured_admission_reference as reader


class MeasuredAdmissionHardlinks(TestCase):
    def fixture(self,root,link_kind=tarfile.LNKTYPE,link_target=None):
        parent=root/'fixtures';parent.mkdir()
        namespace='out/joint-api-qualification/materialized'
        one=namespace+'/one.bin';alias=namespace+'/two.bin'
        body=b'one actual original shared byte body'
        report=b'{"reference":"unchanged"}'
        input=parent/'one.bin';input.write_bytes(body)
        twin=parent/'two.bin';twin.hardlink_to(input)
        path=root/'reference.tar.gz'
        with tarfile.open(path,'w:gz') as tar:
            tar.add(input,arcname=one)
            if link_kind==tarfile.LNKTYPE and link_target is None:
                tar.add(twin,arcname=alias)
            else:
                info=tarfile.TarInfo(alias);info.type=link_kind;info.linkname=link_target or one
                tar.addfile(info)
            info=tarfile.TarInfo(reader.RELATIVE);info.size=len(report)
            tar.addfile(info,io.BytesIO(report))
        digest=lambda b:hashlib.sha256(b).hexdigest()
        lock={'identities':{'reference':{'joint_api':{'qualified_report_sha256':digest(report)}}}}
        return path,lock,{one:digest(body),alias:digest(body)},one,alias,len(body),len(report)

    def test_actual_archiver_hardlink_is_counted_and_restored_without_copy(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);p,lock,expected,one,alias,shared,report=self.fixture(root)
            with patch.object(reader,'ROOT',root),patch.object(reader,'COUNT',3),patch.object(reader,'expected_paths',return_value=expected),patch.object(reader.prior,'TAR_SHA',reader.sha(p)),patch.object(reader.prior,'TAR_BYTES',p.stat().st_size),patch.object(reader.shutil,'disk_usage',return_value=shutil._ntuple_diskusage(32*1024**3,0,32*1024**3)):
                measured=reader.index_archive(p,lock,root)
                self.assertEqual(measured['decoded_bytes'],2*shared+report)
                self.assertEqual(measured['unique_file_bytes'],shared+report)
                self.assertEqual(measured['members'][alias]['linkname'],one)
                self.assertEqual(reader.index_archive(p,lock,root,measured),measured)
                self.assertTrue((root/alias).samefile(root/one))

    def test_symbolic_links_and_unverified_hardlink_targets_are_rejected(self):
        for kind,target in ((tarfile.SYMTYPE,None),(tarfile.LNKTYPE,'out/joint-api-qualification/materialized/missing.bin')):
            with self.subTest(kind=kind),TemporaryDirectory() as tmp:
                root=Path(tmp);p,lock,expected,_,_,_,_=self.fixture(root,kind,target)
                with patch.object(reader,'ROOT',root),patch.object(reader,'COUNT',3),patch.object(reader,'expected_paths',return_value=expected),patch.object(reader.prior,'TAR_SHA',reader.sha(p)),patch.object(reader.prior,'TAR_BYTES',p.stat().st_size):
                    with self.assertRaisesRegex(ValueError,'hardlink'):
                        reader.index_archive(p,lock,root)
