#!/usr/bin/env python3
"""Default and captured CRT corpora remain distinct and reject malformed inputs."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from contracts import ROOT

spec=importlib.util.spec_from_file_location('closeout_crt_reader',ROOT/'Tests/Production/CrtDiagnostic/capture.py')
crt=importlib.util.module_from_spec(spec);spec.loader.exec_module(crt)


class CorpusTests(unittest.TestCase):
    def test_original_default_corpus_preserved(self):
        values=crt.input_values()
        self.assertEqual(len(values),8517)
        self.assertEqual(values,crt.corpus())
        self.assertEqual(values[0],crt.bits(crt.CRITICAL))

    def test_selected_hex_inputs_and_rejections(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'inputs.txt'
            path.write_text('0000000000000000\n3fe0000000000000\n')
            self.assertEqual(crt.input_values(path),['0000000000000000','3fe0000000000000'])
            for body in ('','0000000000000000\n0000000000000000\n','not-hex\n',
                         '7ff0000000000000\n','3ff0000000000001\n','7ff8000000000000\n'):
                path.write_text(body)
                with self.subTest(body=body),self.assertRaises(ValueError):crt.input_values(path)


if __name__=='__main__':unittest.main()
