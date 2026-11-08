#!/usr/bin/env python3
"""Reject partial, skipped or substituted hosted build/test retention."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('hosted_native_package_controls', HERE/'hosted_native_package.py')
hosted = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hosted)


class HostedNativePackageTests(unittest.TestCase):
    def test_real_execution_must_cover_complete_inventory_without_skip_or_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); inventory = root/'inventory.json'; result = root/'results.xml'
            inventory.write_text(json.dumps({'tests': [{'name': 'Original.Math'}, {'name': 'Original.Lua'}]}))
            good = '<testsuite><testcase name="Original.Math"/><testcase name="Original.Lua"/></testsuite>'
            result.write_text(good)
            self.assertEqual(hosted.test_result(inventory, result)['executed_processes'], 2)
            for invalid in (
                '<testsuite/>',
                good.replace('<testcase name="Original.Lua"/>', ''),
                good.replace('Original.Lua', 'Substitute.Lua'),
                good.replace('Original.Lua', 'Original.Math'),
                good.replace('<testcase name="Original.Lua"/>', '<testcase name="Original.Lua"><skipped/></testcase>'),
                good.replace('<testcase name="Original.Lua"/>', '<testcase name="Original.Lua"><failure/></testcase>'),
                good.replace('<testcase name="Original.Lua"/>', '<testcase name="Original.Lua"><error/></testcase>'),
            ):
                with self.subTest(invalid=invalid):
                    result.write_text(invalid)
                    with self.assertRaises(ValueError):
                        hosted.test_result(inventory, result)

    def test_retained_member_requires_exact_bytes_and_safe_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); original = root/'Orbiter.so'; original.write_bytes(b'original runtime')
            self.assertEqual(hosted.checked_member(root, 'Orbiter.so', hosted.sha(original)), original)
            for path, checksum in (('Orbiter.so', '0'*64), ('../Orbiter.so', hosted.sha(original)),
                                   ('/Orbiter.so', hosted.sha(original)), ('C:/Orbiter.so', hosted.sha(original))):
                with self.subTest(path=path):
                    with self.assertRaises(ValueError):
                        hosted.checked_member(root, path, checksum)
            (root/'alias.so').symlink_to(original)
            with self.assertRaises(ValueError):
                hosted.checked_member(root, 'alias.so', hosted.sha(original))

    def test_local_package_or_empty_failed_build_cannot_be_relabelled(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                hosted.package(Path(directory))

    def test_hosted_matrix_keeps_all_profiles_units_and_unsuppressed_sanitizers(self):
        body = (hosted.ROOT/'.github/workflows/phase6-hosted-closeout.yml').read_text()
        self.assertIn('configuration: [Debug, Release]', body)
        self.assertIn('math_profile: [automatic, sse2]', body)
        self.assertIn('--sanitizers --include-unit-tests', body)
        self.assertIn('ctest --test-dir "$PACKAGE/engine"', body)
        self.assertIn('ctest --test-dir "$PACKAGE/upstream-units"', body)
        self.assertIn('LD_PRELOAD="$(c++ -print-file-name=libasan.so)"', body)
        self.assertNotIn('detect_leaks=0', body)
        self.assertNotIn('continue-on-error', body)
        self.assertIn('runs-on: ubuntu-24.04', body)
        self.assertNotIn('self-hosted', body)


if __name__ == '__main__':
    unittest.main()
