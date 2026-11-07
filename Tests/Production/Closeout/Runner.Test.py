#!/usr/bin/env python3
"""Control tests use synthetic captures and real disposable child processes, not simulators."""
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from contracts import Scope, atomic_json, reusable_capture, sha
from processes import OwnedProcess, identity, same_process


class ScopeTests(unittest.TestCase):
    def capture(self, scope):
        return dict(status=scope.terminal, diagnostic_only=scope.selected,
            cases_requested=list(scope.cases), cases={c:dict(runs=[{}, {}]) for c in scope.cases},
            repeats=2, frames=960, failures={}, phase='stock-writer',
            runtime_identity=dict(profile='Debug-automatic'), producer_commit='a'*40,
            runtime_source_commit='b'*40, native_admission_qualified=False, phase6_complete=False)

    def test_full_and_explicit_all_selected_have_different_scope(self):
        full = Scope.make()
        selected = Scope.make(list(full.cases))
        self.assertEqual(full.inspect_terminal(self.capture(full), 'Debug-automatic', 'stock-writer'), 76)
        self.assertEqual(selected.inspect_terminal(self.capture(selected), 'Debug-automatic', 'stock-writer'), 76)
        with self.assertRaisesRegex(ValueError, 'scope/status'):
            full.inspect_terminal(self.capture(selected), 'Debug-automatic', 'stock-writer')

    def test_partial_unknown_duplicate_reordered_selection(self):
        cases = Scope.make().cases
        for selected in ([], ['unknown'], [cases[0], cases[0]], [cases[1], cases[0]]):
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                Scope.make(selected)

    def test_only_terminal_complete_capture_accepted(self):
        scope = Scope.make([Scope.make().cases[2]])
        for change in (dict(status='running'), dict(status='incomplete'), dict(status='failed'),
                       dict(status='audited-incomplete'), dict(failures={'case': 'failure'}),
                       dict(repeats=1), dict(frames=959), dict(phase6_complete=True),
                       dict(cases={}), dict(cases_requested=[]), dict(diagnostic_only=False)):
            report = self.capture(scope)
            report.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                scope.inspect_terminal(report, 'Debug-automatic', 'stock-writer')

    def test_reuse_requires_digest_identity_and_real_audit_callback(self):
        scope = Scope.make([Scope.make().cases[2]])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            atomic_json(root/'capture.json', self.capture(scope))
            digest = sha(root/'capture.json')
            actual = dict(status='audited-native-phase-only', diagnostic_only=True,
                          actual_processes=2, capture_sha256=digest, owning_bytes_unchanged=True)
            inspector = Mock(return_value=actual)
            def reuse(value=digest, runtime='b'*40):
                return reusable_capture(root, value, scope, 'Debug-automatic', 'stock-writer',
                                        'a'*40, runtime, inspector)
            self.assertEqual(reuse(), actual)
            inspector.assert_called_once_with(root, 'Debug-automatic', 'stock-writer', scope.selection)
            with self.assertRaisesRegex(ValueError, 'digest'):
                reuse('0'*64)
            with self.assertRaisesRegex(ValueError, 'identity'):
                reuse(runtime='c'*40)
            for change in (dict(actual_processes=1), dict(diagnostic_only=False), dict(status='audited-incomplete')):
                inspector.return_value = dict(actual, **change)
                with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'audit'):
                    reuse()


class ProcessTests(unittest.TestCase):
    def test_transient_empty_os_argv_is_reobserved_on_the_actual_child(self):
        reads = []
        def transient(pid):
            record = identity(pid)
            reads.append(record)
            return dict(record, argv=[]) if record and len(reads) <= 2 else record
        argv = [sys.executable, '-c', 'import time; time.sleep(30)']
        with patch('processes.identity', side_effect=transient):
            owned = OwnedProcess(argv)
        try:
            actual = owned.receipt()['owned_process_identities'][0]
            self.assertGreaterEqual(len(reads), 3)
            self.assertEqual(actual['pid'], owned.process.pid)
            self.assertEqual(actual['start_ticks'], reads[0]['start_ticks'])
            self.assertEqual(actual['argv'], identity(owned.process.pid)['argv'])
            self.assertEqual(actual['argv'], argv)
        finally:
            owned.cancel()

    def test_missing_os_argv_stays_missing_until_same_process_is_observed(self):
        def empty(pid):
            record = identity(pid)
            return dict(record, argv=[]) if record else None
        argv = [sys.executable, '-c', 'import time; time.sleep(30)']
        started = time.monotonic()
        with patch('processes.identity', side_effect=empty):
            owned = OwnedProcess(argv)
        try:
            self.assertLess(time.monotonic() - started, 2)
            original = owned.receipt()['owned_process_identities'][0]
            self.assertEqual(original['argv'], [])
            # A reused PID must never supply the missing launch identity.
            owned.known[owned.process.pid] = dict(original, start_ticks=original['start_ticks'] + 1)
            owned.discover()
            self.assertEqual(owned.known[owned.process.pid]['argv'], [])
            owned.known[owned.process.pid] = original
            owned.discover()
            actual = owned.known[owned.process.pid]
            self.assertEqual(actual['start_ticks'], original['start_ticks'])
            self.assertEqual(actual['argv'], argv)
        finally:
            owned.known[owned.process.pid] = original
            owned.cancel()

    def test_completed_process_receipt_is_not_cancelled(self):
        owned = OwnedProcess([sys.executable, '-c', 'pass'])
        owned.process.wait(timeout=5)
        receipt = owned.cancel()
        self.assertEqual(receipt['actual_returncode'], 0)
        self.assertTrue(receipt['terminal'])
        self.assertFalse(receipt['cancelled'])

    def test_failure_is_terminal_and_retains_exit_code(self):
        owned = OwnedProcess([sys.executable, '-c', 'raise SystemExit(7)'])
        owned.process.wait(timeout=5)
        self.assertEqual(owned.receipt()['actual_returncode'], 7)
        self.assertTrue(owned.receipt()['terminal'])

    def test_pid_start_token_blocks_reuse(self):
        record = identity(os.getpid())
        self.assertTrue(same_process(record))
        self.assertFalse(same_process(dict(record, start_ticks=record['start_ticks'] + 1)))

    def test_cancellation_includes_new_session_and_preserves_unrelated_process(self):
        with tempfile.TemporaryDirectory() as directory:
            ready = Path(directory)/'ready.json'
            code = ('import subprocess,sys,time,json,signal\n'
                    'child=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"],start_new_session=True)\n'
                    'def stop(*args):\n child.wait(timeout=5)\n raise SystemExit(0)\n'
                    'signal.signal(signal.SIGTERM,stop)\n'
                    'open(sys.argv[1],"w").write(json.dumps({"child":child.pid}))\n'
                    'time.sleep(30)\n')
            unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
            owned = OwnedProcess([sys.executable, '-c', code, str(ready)])
            try:
                deadline = time.monotonic() + 5
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(ready.exists())
                child = json.loads(ready.read_text())['child']
                self.assertIn(child, {r['pid'] for r in owned.discover()})
                receipt = owned.cancel()
                self.assertTrue(receipt['terminal'] and receipt['cancelled'])
                current = identity(child)
                self.assertTrue(current is None or current['state'] == 'Z')
                self.assertIsNone(unrelated.poll())
            finally:
                owned.cancel()
                unrelated.terminate()
                unrelated.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
