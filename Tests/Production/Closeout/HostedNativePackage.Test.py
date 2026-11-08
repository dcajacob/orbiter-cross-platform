#!/usr/bin/env python3
"""Reject partial, skipped or substituted hosted build/test retention."""
import importlib.util
import json
import hashlib
from pathlib import Path
import subprocess
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

    def test_failed_units_retain_raw_bundle_without_becoming_a_success(self):
        (hosted.ROOT/'out').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=hosted.ROOT/'out') as directory:
            package = Path(directory)/'fixture'; package.mkdir()
            binary = package/'fixture-runtime'; binary.write_bytes(b'disposable retention control, not a simulator')
            relative = binary.relative_to(hosted.ROOT).as_posix()
            source_name = 'README.md'
            source_hash = hashlib.sha256((hosted.ROOT/source_name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            record = dict(status='built', source_base=subprocess.check_output(['git','-C',str(hosted.ROOT),'rev-parse','HEAD'],text=True).strip(),
                owning_sources_unchanged=True, instrumentation='address,undefined', source_sha256_lf={source_name:source_hash},
                dependency_sha256_lf={}, runtime_files_sha256={relative:hosted.sha(binary)},
                candidate_runtime_files_sha256={}, generated_source_files_sha256={},
                configuration='Debug', math_profile='sse2', builder_sha256=hosted.sha(hosted.__file__))
            (package/'build.json').write_text(json.dumps(record))
            inventory={'tests':[{'name':'original'}]}
            for prefix in ('registered', 'upstream-registered'):
                (package/(prefix+'-unit-tests.json')).write_text(json.dumps(inventory))
            (package/'engine-tests.xml').write_text('<testsuite><testcase name="original"><failure/></testcase></testsuite>')
            (package/'upstream-tests.xml').write_text('<testsuite><testcase name="original"/></testsuite>')
            for kind in ('lua','collision'):
                (package/('upstream-'+kind+'-case-inventory.txt')).write_text('1 test case\n')
            with self.assertRaises(ValueError):
                hosted.package(package)
            report=json.loads((package/'hosted-package.json').read_text())
            self.assertEqual(report['status'],'built-only-tests-failed-or-incomplete')
            self.assertIn('engine',report['test_errors'])
            self.assertEqual(report['tests']['upstream']['executed_processes'],1)
            self.assertTrue(package.with_suffix('.tar.gz').is_file())
            self.assertEqual(report['archive_members_sha256'][relative],hosted.sha(binary))
            self.assertFalse(report['native_admission_qualified'])
            self.assertFalse(report['phase6_complete'])

    def test_hosted_matrix_keeps_all_profiles_units_and_unsuppressed_sanitizers(self):
        body = (hosted.ROOT/'.github/workflows/phase6-hosted-closeout.yml').read_text()
        self.assertIn('configuration: [Debug, Release]', body)
        self.assertIn('math_profile: [automatic, sse2]', body)
        self.assertIn('--sanitizers --include-unit-tests', body)
        self.assertIn('ctest --test-dir "$PACKAGE/engine"', body)
        self.assertIn('ctest --test-dir "$PACKAGE/upstream-units"', body)
        self.assertIn('LD_PRELOAD="$(c++ -print-file-name=libasan.so)"', body)
        self.assertIn('export PYTHONMALLOC=malloc', body)
        self.assertIn('needs: [controls, sanitizer-launcher-controls]', body)
        self.assertNotIn('detect_leaks=0', body)
        self.assertNotIn('continue-on-error', body)
        self.assertIn('runs-on: ubuntu-24.04', body)
        self.assertNotIn('self-hosted', body)

    def test_windows_retry_does_not_duplicate_the_active_native_builds(self):
        body = (hosted.ROOT/'.github/workflows/phase6-hosted-closeout.yml').read_text()
        native = body.split('  native-package:\n', 1)[1]
        self.assertIn("if: github.ref != 'refs/heads/qualification/windows-client-retry'", native)
        windows = (hosted.ROOT/'.github/workflows/production-client.yml').read_text()
        self.assertEqual(windows.count('"-DCMAKE_POLICY_VERSION_MINIMUM=3.5"'), 2)
        self.assertNotIn(' -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ', windows)

    def test_native_retry_preserves_active_windows_work(self):
        body = (hosted.ROOT/'.github/workflows/phase6-hosted-closeout.yml').read_text()
        windows = body.split('  windows-client:\n', 1)[1].split('  sanitizer-launcher-controls:\n', 1)[0]
        self.assertIn("if: github.ref != 'refs/heads/qualification/native-package-retry'", windows)


if __name__ == '__main__':
    unittest.main()
