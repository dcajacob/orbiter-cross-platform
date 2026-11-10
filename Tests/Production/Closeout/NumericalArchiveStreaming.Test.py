from io import BytesIO
from pathlib import Path
import tempfile
from unittest import TestCase,mock
import gzip,hashlib,tarfile
import rejection_input_bundle as bundle
import stream_retained_numerical_inputs as stream


class NumericalArchiveStreaming(TestCase):
    def fixture(self,root):
        out=root/'out';out.mkdir();a=out/'actual-physics.csv';b=out/'large-original-planet';a.write_bytes(b'0,exact');b.write_bytes(b'complete original input')
        alias=out/'input-alias';alias.symlink_to(b.name)
        index=bundle.pack(root,{a,b,alias},out/'retained.tar.gz',out/'index.json')
        body=(out/'retained.tar.gz').read_bytes();a.unlink();alias.unlink();b.unlink();return body,index

    def test_every_body_and_symbolic_alias_is_verified_without_copying_unused_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);body,index=self.fixture(root)
            with mock.patch('stream_retained_numerical_inputs.shutil.disk_usage',return_value=mock.Mock(free=16*1024**3)):
                checked,proof=stream.verify(root,BytesIO(body),index,{'out/actual-physics.csv'},root/'out/objects')
            self.assertEqual(checked,{n:v['sha256'] for n,v in index['files'].items()})
            self.assertEqual(proof['actual_auditor_inputs_materialized'],1)
            self.assertEqual((root/'out/actual-physics.csv').read_bytes(),b'0,exact')
            self.assertFalse((root/'out/large-original-planet').exists())

    def test_changed_unused_actual_body_fails_even_with_rehashed_compressed_stream(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);body,index=self.fixture(root)
            altered=gzip.compress(gzip.decompress(body).replace(b'complete original input',b'changed! original input'))
            index.update(archive_bytes=len(altered),archive_sha256=hashlib.sha256(altered).hexdigest())
            with mock.patch('stream_retained_numerical_inputs.shutil.disk_usage',return_value=mock.Mock(free=16*1024**3)):
                with self.assertRaisesRegex(ValueError,'Actual original regular raw bytes differ'):
                    stream.verify(root,BytesIO(altered),index,{'out/actual-physics.csv'},root/'out/objects')
