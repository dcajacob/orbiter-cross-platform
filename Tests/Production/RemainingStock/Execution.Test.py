#!/usr/bin/env python3
"""Exercise real isolated subprocesses, complete case collection and timeout cleanup."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

from execution import collect, run_process


class ExecutionTests(unittest.TestCase):
    def test_complete_scene_pairs_and_main_thread_records(self):
        cases = json.loads((Path(__file__).parent/'cases.json').read_text())['cases']
        self.assertEqual(len(cases), 38)
        owner = threading.get_ident()
        barrier = threading.Barrier(2, timeout=10)
        lock = threading.Lock()
        active = 0
        peak = 0
        recorded = {}
        with tempfile.TemporaryDirectory(prefix='orbiter-scene-workers-') as temporary:
            root = Path(temporary)
            def observe(case):
                nonlocal active, peak
                with lock:
                    active += 1
                    peak = max(peak, active)
                try:
                    if case['id'] in (cases[0]['id'], cases[1]['id']):
                        barrier.wait()
                    result = []
                    for repeat in (1, 2):
                        directory = root/(case['id']+'-'+str(repeat))
                        directory.mkdir()
                        body = "from pathlib import Path; import sys; Path('identity.txt').write_text(sys.argv[1])"
                        identity = case['id']+'/'+str(repeat)
                        process = run_process([sys.executable, '-B', '-c', body, identity], directory, 10)
                        self.assertEqual(process.returncode, 0)
                        self.assertEqual((directory/'identity.txt').read_text(), identity)
                        self.assertFalse(json.loads((directory/'process-timing.json').read_text())['timed_out'])
                        result.append(identity)
                    return result
                finally:
                    with lock:
                        active -= 1
            def record(case, result, error):
                self.assertEqual(threading.get_ident(), owner)
                self.assertIsNone(error)
                self.assertNotIn(case['id'], recorded)
                recorded[case['id']] = result
            collect(cases, 2, observe, record)
            self.assertEqual(set(recorded), {case['id'] for case in cases})
            self.assertEqual(peak, 2)
            self.assertEqual(active, 0)
            for case in cases:
                self.assertEqual(recorded[case['id']], [case['id']+'/1', case['id']+'/2'])

    def test_failed_case_does_not_drop_later_cases(self):
        cases = [dict(id=str(i)) for i in range(8)]
        results = {}
        def observe(case):
            if case['id'] == '2':
                raise ValueError('Retained real worker failure')
            return case['id']
        def record(case, result, error):
            self.assertNotIn(case['id'], results)
            results[case['id']] = (result, error)
        collect(cases, 2, observe, record)
        self.assertEqual(set(results), {case['id'] for case in cases})
        self.assertIsInstance(results['2'][1], ValueError)
        self.assertEqual(str(results['2'][1]), 'Retained real worker failure')
        for case in cases:
            if case['id'] != '2':
                self.assertEqual(results[case['id']], (case['id'], None))

    def test_duplicate_empty_and_invalid_scope_never_launch(self):
        def unexpected(*args):
            self.fail('Invalid scope launched a worker or wrote a report')
        for cases in ([], [dict(id='same'), dict(id='same')]):
            with self.assertRaises(ValueError):
                collect(cases, 2, unexpected, unexpected)
        for workers in (0, 5, -1, True, 1.5):
            with self.assertRaises(ValueError):
                collect([dict(id='one')], workers, unexpected, unexpected)

    def test_timeout_retains_reaped_actual_process_result(self):
        with tempfile.TemporaryDirectory(prefix='orbiter-scene-timeout-') as temporary:
            directory = Path(temporary)
            with self.assertRaises(subprocess.TimeoutExpired):
                run_process([sys.executable, '-B', '-c', 'import time; time.sleep(5)'], directory, .1)
            timing = json.loads((directory/'process-timing.json').read_text())
            result = json.loads((directory/'process-result.json').read_text())
            self.assertTrue(timing['timed_out'])
            self.assertEqual(timing['timeout_seconds'], .1)
            self.assertGreater(timing['elapsed_wall_ns'], 0)
            self.assertIsNotNone(timing['actual_returncode'])
            self.assertNotEqual(result['returncode'], 0)
            self.assertEqual(result['returncode'], timing['actual_returncode'])

    def test_nonzero_exit_and_output_are_retained(self):
        with tempfile.TemporaryDirectory(prefix='orbiter-scene-nonzero-') as temporary:
            directory = Path(temporary)
            body = "import sys; print('retained stdout'); print('retained stderr', file=sys.stderr); sys.exit(7)"
            process = run_process([sys.executable, '-B', '-c', body], directory, 10)
            self.assertEqual(process.returncode, 7)
            self.assertEqual(json.loads((directory/'process-result.json').read_text()), dict(returncode=7))
            timing = json.loads((directory/'process-timing.json').read_text())
            self.assertFalse(timing['timed_out'])
            self.assertEqual(timing['actual_returncode'], 7)
            self.assertIn('retained stdout', (directory/'console.txt').read_text())
            self.assertIn('retained stderr', (directory/'console.txt').read_text())

    def test_invalid_deadline_never_launches(self):
        with tempfile.TemporaryDirectory(prefix='orbiter-scene-bad-deadline-') as temporary:
            directory = Path(temporary)
            for limit in (0, -1, 901, float('nan'), float('inf')):
                with self.assertRaises(ValueError):
                    run_process([sys.executable, '-B', '-c', 'raise SystemExit(0)'], directory, limit)
            self.assertEqual(list(directory.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
