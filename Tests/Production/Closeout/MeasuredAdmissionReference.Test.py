import hashlib
import io
import json
import shutil
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import measured_admission_reference as reader


class MeasuredAdmissionReference(TestCase):
    def fixture(self,root,duplicate=False):
        p=root/'reference.tar.gz'
        report=json.dumps({'scope':'qualified reference fixture only'}).encode()
        entry='out/joint-api-qualification/materialized/input.bin'
        files={entry:b'whole fixture original evidence',reader.RELATIVE:report}
        with tarfile.open(p,'w:gz') as archive:
            for name,data in [*files.items(),*([(entry,files[entry])] if duplicate else [])]:
                info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644
                archive.addfile(info,io.BytesIO(data))
        digest=lambda data:hashlib.sha256(data).hexdigest()
        lock={'identities':{'reference':{'joint_api':{'qualified_report_sha256':digest(report)}}}}
        return p,lock,{entry:digest(files[entry])},files

    def test_exact_real_stream_measures_and_restores_original_bodies(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);p,lock,expected,files=self.fixture(root)
            with patch.object(reader,'ROOT',root),patch.object(reader,'COUNT',2),patch.object(reader,'expected_paths',return_value=expected),patch.object(reader.prior,'TAR_SHA',reader.sha(p)),patch.object(reader.prior,'TAR_BYTES',p.stat().st_size),patch.object(reader.shutil,'disk_usage',return_value=shutil._ntuple_diskusage(32*1024**3,0,32*1024**3)):
                result=reader.index_archive(p,lock,root)
                self.assertEqual(result['decoded_bytes'],sum(map(len,files.values())))
                self.assertEqual(reader.index_archive(p,lock,root,result),result)
                for name,data in files.items():self.assertEqual((root/name).read_bytes(),data)

    def test_duplicate_original_member_is_rejected_before_use(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);p,lock,expected,_=self.fixture(root,True)
            with patch.object(reader,'COUNT',3),patch.object(reader,'expected_paths',return_value=expected),patch.object(reader.prior,'TAR_SHA',reader.sha(p)),patch.object(reader.prior,'TAR_BYTES',p.stat().st_size):
                with self.assertRaisesRegex(ValueError,'Canonical unique'):
                    reader.index_archive(p,lock,root)

    def test_actual_decoded_capacity_keeps_eight_GiB_reserve(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);p,lock,expected,files=self.fixture(root)
            with patch.object(reader,'COUNT',2),patch.object(reader,'expected_paths',return_value=expected),patch.object(reader.prior,'TAR_SHA',reader.sha(p)),patch.object(reader.prior,'TAR_BYTES',p.stat().st_size):
                result=reader.index_archive(p,lock,root)
                with patch.object(reader.shutil,'disk_usage',return_value=shutil._ntuple_diskusage(reader.RESERVE,0,reader.RESERVE)):
                    with self.assertRaisesRegex(ValueError,'eight GiB'):
                        reader.index_archive(p,lock,root,result)
