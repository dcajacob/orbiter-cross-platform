"""Synthetic paused controls cannot hide lost links, missing F5 or partial worlds."""
import copy
import csv
import os
from pathlib import Path
import tempfile
import unittest

from class_eligibility import inspect_paused, OBJECTS
from contracts import atomic_json, sha


def write_csv(path, records):
    with path.open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


class PausedEvidenceControls(unittest.TestCase):
    def test_incomplete_and_damaged_closed_controls_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = root / 'synthetic-executable'
            executable.write_bytes(b'Synthetic fixture; no simulator or acceptance credit.')
            frame = root / 'scene.rgba'
            with frame.open('wb') as stream: stream.truncate(1280 * 720 * 4)
            life = dict(rendered_frames=60, successful_presents=60, context_deleted=True)
            states = [dict(object=name, **{'class': kind}, tick='0', seconds='0', mass='100',
                           dock='ISS' if name == 'STS-101' else '',
                           attached='Leonardo;' if name == 'STS-101' else 'STS-101;' if name == 'Leonardo' else '')
                      for name, kind in OBJECTS.items()]
            (root / 'console.log').write_text('Synthetic clean fixture\n')
            events = [dict(key=63, down=1), dict(key=63, down=0)]
            for index in range(1, 21):
                folder = root if index == 1 else root / ('session-' + str(index))
                folder.mkdir(exist_ok=True)
                if index > 1: os.link(frame, folder / 'scene.rgba')
                atomic_json(folder / 'graphics-lifecycle.json', life)
                write_csv(folder / 'flight-state.csv', states)
                if index < 20: write_csv(folder / 'input-events.csv', events)
                else: (folder / 'input-events.csv').write_text('key,down\n')
            keys = [dict(code=code, down=down, monotonic_ns=i + 1)
                    for i, (code, down) in enumerate([(63, True), (63, False)] * 19 + [(1, True)])]
            report = dict(status='passed-actual-paused-attached-docked-world-lifetimes',
                requested_worlds=20, worlds_observed_ready=20, clean_contexts=20, actual_exitcode=0,
                actual_pid=123, no_preload_observer=True, sanitizer_suppressions=False,
                all_guarded_inputs_unchanged=True, native_admission_qualified=False, phase6_complete=False,
                original_objects=OBJECTS, guarded_files_sha256={str(executable): sha(executable)},
                actual_executable=str(executable), actual_executable_sha256=sha(executable),
                physical_keys=keys, lifecycles=[life] * 20, successful_presents=1200,
                finite_original_vessel_rows=60, runtime_identity={'profile': 'synthetic-control-only'})
            path = root / 'verification.json'
            atomic_json(path, report)
            self.assertEqual(inspect_paused(path)['real_F5_reloads'], 19)
            for change in (dict(status='running'), dict(worlds_observed_ready=19), dict(actual_exitcode=7),
                           dict(sanitizer_suppressions=True), dict(guarded_files_sha256={}),
                           dict(physical_keys=keys[:-1]), dict(native_admission_qualified=True)):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    atomic_json(path, dict(report, **change))
                    inspect_paused(path)
            atomic_json(path, report)
            for change in (dict(attached=''), dict(mass='nan'), dict(seconds='1')):
                damaged = copy.deepcopy(states)
                damaged[1].update(change)
                with self.subTest(change=change), self.assertRaises(ValueError):
                    write_csv(root / 'flight-state.csv', damaged)
                    inspect_paused(path)
            write_csv(root / 'flight-state.csv', states)
            write_csv(root / 'input-events.csv', events[:1])
            with self.assertRaisesRegex(ValueError, 'nineteen'):
                inspect_paused(path)


if __name__ == '__main__': unittest.main()
