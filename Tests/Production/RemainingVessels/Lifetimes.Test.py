"""Reject incomplete lifetimes, lost vessels, sanitizer errors and retained DSOs."""
import csv
from pathlib import Path
import tempfile
import unittest

from lifetimes import inspect_loader, inspect_world, FRAMES, SESSIONS
from contracts import atomic_json


class LifetimeControls(unittest.TestCase):
    def fixture(self, root):
        atomic_json(root / 'graphics-lifecycle.json',
                    dict(rendered_frames=FRAMES, successful_presents=FRAMES, context_deleted=True))
        with (root / 'scene.rgba').open('wb') as stream:
            stream.truncate(1280 * 720 * 4)
        return [dict(tick=tick, object=name, **{'class': kind}, seconds=tick / 64, mass=100)
                for tick in range(FRAMES + 1) for name, kind in [('Telescope', 'HST'), ('GL', 'DeltaGlider')]]

    def write(self, root, records):
        with (root / 'flight-state.csv').open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=['tick', 'object', 'class', 'seconds', 'mass'])
            writer.writeheader()
            writer.writerows(records)

    def test_complete_roster_all_ticks_and_graphics_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            records = self.fixture(root)
            expected = {'Telescope': 'HST', 'GL': 'DeltaGlider'}
            self.write(root, records)
            self.assertEqual(inspect_world(root, expected)['finalized_ticks'], 61)
            damaged = [records[:-1], records[2:], records + [records[-1]],
                       [dict(r, mass='nan') if i == 30 else r for i, r in enumerate(records)],
                       [dict(r, **{'class': 'Generic'}) if i == 20 else r for i, r in enumerate(records)]]
            for index, data in enumerate(damaged):
                with self.subTest(index=index), self.assertRaises(ValueError):
                    self.write(root, data)
                    inspect_world(root, expected)
            self.write(root, records)
            for change in (dict(context_deleted=False), dict(successful_presents=59), dict(rendered_frames=61)):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    atomic_json(root / 'graphics-lifecycle.json', dict(
                        dict(rendered_frames=FRAMES, successful_presents=FRAMES, context_deleted=True), **change))
                    inspect_world(root, expected)

    def test_truncated_frame_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            records = self.fixture(root)
            self.write(root, records)
            (root / 'scene.rgba').write_bytes(b'partial')
            with self.assertRaisesRegex(ValueError, 'frame'):
                inspect_world(root, {'Telescope': 'HST', 'GL': 'DeltaGlider'})

    def test_real_loader_spelling_and_retention_controls(self):
        module = '/owner/engine/NativeModules/Vessel/SolarSail.so'
        cycle = (f'  123: calling init: {module}\n\n'
                 f'  123: calling fini: {module} [0]\n\n'
                 f'  123: file={module} [0];  destroying link map\n')
        good = cycle * SESSIONS
        self.assertEqual(inspect_loader(good, ['SolarSail'])['SolarSail']['destroyed_link_maps'], 20)
        for bad in (cycle * 19, good + cycle, good.replace('destroying link map', 'retained'),
                    good.replace('/Vessel/', '/Fake/'), good.replace('calling fini', 'skipping fini')):
            with self.subTest(bad=bad[:70]), self.assertRaises(ValueError):
                inspect_loader(bad, ['SolarSail'])


if __name__ == '__main__':
    unittest.main()
