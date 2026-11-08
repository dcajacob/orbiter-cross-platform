#!/usr/bin/env python3
"""A replacement container cannot change or omit any frozen data input."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from contracts import ROOT, atomic_json, sha


class ProvisioningContainerTests(unittest.TestCase):
    def fixture(self, root):
        files = {'Kernels/orbiter.bsp': b'frozen kernel', 'Fonts/test.ttf': b'frozen glyphs'}
        for name, note in [('original.zip', b'old container'), ('replacement.zip', b'new container')]:
            with zipfile.ZipFile(root / name, 'w') as archive:
                for path, body in files.items():
                    archive.writestr(path, body)
                archive.writestr('container-note.txt', note)
        original = root / 'original.zip'
        profile = dict(repository='orbitersim/orbiter', url='https://github.com/orbitersim/orbiter/releases/download/frozen/original.zip',
            bytes=original.stat().st_size, sha256=sha(original),
            data_files={name: dict(bytes=len(body), sha256=hashlib.sha256(body).hexdigest()) for name, body in files.items()})
        atomic_json(root / 'profile.json', profile)
        replacement = root / 'replacement.zip'
        variant = dict(protocol='production-stock-container-v1', repository=profile['repository'],
            url='https://github.com/orbitersim/orbiter/releases/download/recorded/replacement.zip',
            bytes=replacement.stat().st_size, sha256=sha(replacement), original_profile_sha256=sha(root / 'profile.json'))
        atomic_json(root / 'container.json', variant)
        return profile, variant, files

    def run_prepare(self, root, archive, destination, explicit=True, environment=False, profile='profile.json'):
        args = [sys.executable, '-B', str(ROOT / 'Tests/Production/prepare_data.py'),
                '--lock', str(root / profile), '--archive', str(root / archive),
                '--destination', str(root / destination)]
        env = dict(os.environ)
        env.pop('ORBITER_DATA_CONTAINER_LOCK', None)
        if explicit and not environment:
            args += ['--container-lock', str(root / 'container.json')]
        if environment:
            env['ORBITER_DATA_CONTAINER_LOCK'] = str(root / 'container.json')
        return subprocess.run(args, env=env, capture_output=True, text=True)

    def test_both_declared_containers_retain_identical_frozen_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profile, variant, files = self.fixture(root)
            profile_hash = sha(root / 'profile.json')
            for archive in ('original.zip', 'replacement.zip'):
                result = self.run_prepare(root, archive, archive + '-output')
                self.assertEqual(result.returncode, 0, result.stderr)
                receipt = json.loads(result.stdout.splitlines()[-1])
                self.assertEqual(receipt['original_package_sha256'], profile['sha256'])
                self.assertEqual(receipt['actual_container_sha256'], sha(root / archive))
                for name, body in files.items():
                    self.assertEqual((root / (archive + '-output') / name).read_bytes(), body)
            self.assertNotEqual(profile['sha256'], variant['sha256'])
            self.assertEqual(profile_hash, sha(root / 'profile.json'))
            self.assertNotEqual(self.run_prepare(root, 'replacement.zip', 'undeclared', explicit=False).returncode, 0)
            result = self.run_prepare(root, 'replacement.zip', 'env-output', environment=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_job_stock_override_does_not_apply_to_the_separate_planet_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profile, variant, unused = self.fixture(root)
            # Another independently locked package may share files, but must
            # retain its own original archive identity under the job-wide env.
            other = dict(profile, repository='standard/planets')
            atomic_json(root / 'planets.json', other)
            result = self.run_prepare(root, 'original.zip', 'planets-output', explicit=False,
                                      environment=True, profile='planets.json')
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = json.loads(result.stdout.splitlines()[-1])
            self.assertEqual(receipt['actual_container_sha256'], profile['sha256'])
            self.assertIsNone(receipt['versioned_container_lock_sha256'])

    def test_changed_kernel_missing_font_and_foreign_profile_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profile, variant, files = self.fixture(root)
            for mode in ('changed-kernel', 'missing-font', 'foreign-profile'):
                path = root / (mode + '.zip')
                with zipfile.ZipFile(path, 'w') as archive:
                    for name, body in files.items():
                        if mode == 'missing-font' and name.startswith('Fonts/'):
                            continue
                        archive.writestr(name, b'changed kernel' if mode == 'changed-kernel' and name.startswith('Kernels/') else body)
                declared = dict(variant, bytes=path.stat().st_size, sha256=sha(path))
                if mode == 'foreign-profile':
                    declared['original_profile_sha256'] = '0' * 64
                atomic_json(root / 'container.json', declared)
                with self.subTest(mode=mode):
                    self.assertNotEqual(self.run_prepare(root, path.name, mode + '-output').returncode, 0)


if __name__ == '__main__':
    unittest.main()
