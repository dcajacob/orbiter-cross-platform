"""Exercise source conservation, cross-volume caching and private replacements."""
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from LocalVM.static_binary_link_staging_v2 import BinaryLinks, sha


class StagingControls(unittest.TestCase):
    def fixture(self, root):
        source = root / 'canonical.bin'
        source.write_bytes(bytes(range(256)) * 17)
        output = root / 'output'
        output.mkdir()
        return source, output, BinaryLinks({str(source): sha(source)}, output)

    def test_same_volume_links_and_private_copy_detaches(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, output, links = self.fixture(root)
            target = output / 'staged.bin'
            links.copy2(source, target)
            self.assertEqual(source.stat().st_ino, target.stat().st_ino)
            private = root / 'private.bin'
            private.write_bytes(b'private replacement')
            links.copy2(private, target)
            self.assertEqual(target.read_bytes(), b'private replacement')
            self.assertNotEqual(source.stat().st_ino, target.stat().st_ino)
            links.close()

    def test_cross_volume_cache_is_shared_and_origin_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, output, links = self.fixture(Path(temporary))
            with patch.object(links, 'same_volume', return_value=False):
                links.copy2(source, output / 'one.bin')
                links.copy2(source, output / 'two.bin')
            self.assertEqual(len(links.cached), 1)
            self.assertEqual((output / 'one.bin').stat().st_ino, (output / 'two.bin').stat().st_ino)
            self.assertNotEqual(source.stat().st_ino, (output / 'one.bin').stat().st_ino)
            self.assertEqual(sha(source), sha(output / 'one.bin'))
            links.close()

    def test_changed_source_and_changed_cache_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, output, links = self.fixture(Path(temporary))
            with patch.object(links, 'same_volume', return_value=False):
                links.copy2(source, output / 'one.bin')
                (output / 'one.bin').write_bytes(b'corrupted cache through actual hardlink')
                with self.assertRaisesRegex(ValueError, 'cache'):
                    links.copy2(source, output / 'two.bin')
            with self.assertRaisesRegex(ValueError, 'cache'): links.close()
            source.write_bytes(b'changed source')
            with self.assertRaisesRegex(ValueError, 'Canonical'): links.close()

    def test_unguarded_inputs_are_copied_and_hardlink_failure_falls_back(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, output, links = self.fixture(root)
            ordinary = root / 'unguarded.bin'
            ordinary.write_bytes(source.read_bytes())
            links.copy2(ordinary, output / 'unguarded.bin')
            self.assertNotEqual(ordinary.stat().st_ino, (output / 'unguarded.bin').stat().st_ino)
            with patch('os.link', side_effect=OSError('control: hardlinks unavailable')):
                links.copy2(source, output / 'fallback.bin')
            self.assertEqual(len(links.fallback), 1)
            self.assertEqual(sha(source), sha(output / 'fallback.bin'))
            links.close()

    def test_output_escape_canonical_overwrite_and_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, output, links = self.fixture(root)
            for target in (source,):
                with self.assertRaises(ValueError): links.copy2(source, target)
            (output / 'escape').symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'escapes'):
                links.copy2(source, output / 'escape' / 'external.bin')
            with self.assertRaisesRegex(ValueError, 'overlaps'):
                BinaryLinks({str(source): sha(source)}, root)
            links.close()

    def test_install_close_restores_real_copy_function(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, output, links = self.fixture(Path(temporary))
            original = shutil.copy2
            try:
                links.install()
                shutil.copy2(source, output / 'linked.bin')
                self.assertEqual(source.stat().st_ino, (output / 'linked.bin').stat().st_ino)
            finally: links.close()
            self.assertIs(shutil.copy2, original)
            links.close()

    def test_samples_are_bounded_without_shortening_actual_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, output, links = self.fixture(Path(temporary))
            for i in range(140): links.copy2(source, output / ('copy-' + str(i)))
            receipt = links.receipt()
            self.assertEqual(receipt['actual_link_count'], 140)
            self.assertEqual(sum(receipt['linked_input_counts'].values()), 140)
            self.assertEqual(len(receipt['link_samples']), 128)
            links.close()


if __name__ == '__main__': unittest.main()
