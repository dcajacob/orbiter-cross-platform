#!/usr/bin/env python3
"""Controls for ordinary-session launch evidence; no simulator acceptance credit."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from contracts import ROOT, atomic_json, load, sha
from interactive_launch import HELPER, RUNNER, PROTOCOL, sources, validate
from receipts import inspect_launch

HERE = Path(__file__).resolve().parent


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


legacy = module(HERE / 'Receipts.Test.py', 'interactive_legacy_receipt_fixture')
sys.path.insert(0, str(HERE / 'LocalVM'))
runner = module(HERE / 'LocalVM' / RUNNER, 'interactive_runner_controls')


def fixture(root):
    pins, old = legacy.fixture(root)
    for name in list(pins):
        if name != 'worker.py':
            (root / 'scripts' / name).unlink()
            del pins[name]
    for name in (RUNNER, HELPER):
        (root / 'scripts' / name).write_bytes((HERE / 'LocalVM' / name).read_bytes())
        pins[name] = sha(root / 'scripts' / name)
    cfg = load(root / 'request.json')
    cfg.update(desktop='Default', bootstrap_script='Z:/Phase6/scripts/' + RUNNER,
               bootstrap_sha256=pins[RUNNER])
    cfg['interactive_launch'] = dict(protocol=PROTOCOL, nonce='a' * 32,
        python='C:/Python/python.exe', worker_result='worker-result.json',
        domain_name='win11', domain_uuid=old['vm']['domain_uuid'])
    atomic_json(root / 'runners.json', dict(commit=cfg['roles']['runner']['commit'], files_sha256=pins))
    cfg['roles']['runner']['manifest_sha256'] = sha(root / 'runners.json')
    atomic_json(root / 'request.json', cfg)
    worker = old['worker-result']
    worker.update(context=dict(session=2, window_station='WinSta0', desktop='Default'),
                  request_sha256=sha(root / 'request.json'), roles=cfg['roles'])
    atomic_json(root / 'worker-result.json', worker)
    (root / 'interactive-worker.log').write_text('actual control log\n')
    started = dict(protocol=PROTOCOL, nonce='a' * 32, status='started-interactive-windows-worker',
        request_sha256=sha(root / 'request.json'), context=worker['context'], platform='win32', elevated=False,
        actual_runner_pid=100, actual_worker_pid=101, actual_machine_uuid=cfg['interactive_launch']['domain_uuid'],
        worker_start_identity=dict(kind='windows-process-creation-filetime', value=12345),
        runner_sha256=pins[RUNNER], helper_sha256=pins[HELPER], worker_sha256=pins['worker.py'],
        scripts_sha256=pins, python=cfg['interactive_launch']['python'],
        worker_argv=['-B', cfg['worker_script'], cfg['request_path']])
    finished = dict(started, status='completed-interactive-windows-worker', actual_worker_returncode=0,
        inputs_unchanged=True, elapsed_wall_ns=100, worker_result_sha256=sha(root / 'worker-result.json'),
        worker_log_sha256=sha(root / 'interactive-worker.log'))
    atomic_json(root / 'interactive-started.json', started)
    atomic_json(root / 'interactive-result.json', finished)
    return pins, cfg, started, finished


class InteractiveTests(unittest.TestCase):
    def test_completed_ordinary_session_and_missing_exit_identity_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pins, cfg, started, finished = fixture(root)
            inspect_launch(root, pins)
            for update in (dict(status='failed'), dict(actual_worker_returncode=1), dict(nonce='b' * 32),
                           dict(actual_worker_pid=True), dict(actual_worker_pid=100), dict(elevated=True),
                           dict(actual_machine_uuid='4b599191-901c-4578-9706-ba2763d030b7'),
                           dict(worker_start_identity=dict(kind='windows-process-creation-filetime', value=0)),
                           dict(context=dict(session=0, window_station='Service-0', desktop='Default')),
                           dict(worker_argv=['-B', cfg['worker_script'], 'Z:/Other/request.json']),
                           dict(inputs_unchanged=False), dict(elapsed_wall_ns=0), dict(worker_result_sha256='0' * 64)):
                atomic_json(root / 'interactive-result.json', dict(finished, **update))
                with self.subTest(update=update), self.assertRaises(ValueError):
                    inspect_launch(root, pins)
            atomic_json(root / 'interactive-result.json', finished)
            (root / 'interactive-worker.log').write_text('replaced log')
            with self.assertRaises(ValueError):
                inspect_launch(root, pins)

    def test_private_receipts_cannot_be_relabelled_as_interactive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pins, old = legacy.fixture(root)
            cfg = load(root / 'request.json')
            cfg['interactive_launch'] = dict(protocol=PROTOCOL, nonce='a' * 32)
            atomic_json(root / 'request.json', cfg)
            with self.assertRaises(ValueError):
                inspect_launch(root, pins)

    def test_context_scope_capacity_role_and_source_controls_remain_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pins, cfg, unused, finished = fixture(root)
            for mutate in (lambda v: v.update(desktop='Private'),
                           lambda v: v.update(active_session=0),
                           lambda v: v.update(scene_workers=2),
                           lambda v: v.update(minimum_free_bytes=1),
                           lambda v: v['roles']['sdk'].update(commit='f' * 40),
                           lambda v: v['interactive_launch'].update(worker_result='../result.json')):
                bad = copy.deepcopy(cfg)
                mutate(bad)
                atomic_json(root / 'request.json', bad)
                with self.assertRaises(ValueError):
                    inspect_launch(root, pins)
            atomic_json(root / 'request.json', cfg)
            (root / 'scripts' / HELPER).write_text('# changed helper\n')
            with self.assertRaises(ValueError):
                inspect_launch(root, pins)

    def test_legacy_and_interactive_source_closures_stay_distinct(self):
        old = {name: name for name in ('worker.py', 'win_local_process_v1.py',
                                      'system_user_launcher_v1.py', 'private_desktop_bootstrap_v1.py')}
        self.assertEqual(sources(old, old), old)
        fresh = sources({'worker.py', RUNNER, HELPER}, old)
        self.assertEqual(set(fresh), {'worker.py', RUNNER, HELPER})
        with self.assertRaises(ValueError):
            sources(set(fresh) | {'system_user_launcher_v1.py'}, old)

    def test_actual_subprocess_exit_and_exclusive_session_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            observed = []
            code = runner.observe_child([sys.executable, '-c', 'print("ordinary child");raise SystemExit(7)'],
                root, root / 'child.log', lambda process: dict(kind='control-only', value=process.pid),
                lambda pid, identity: observed.append((pid, identity)))
            self.assertEqual(code, 7)
            self.assertEqual((root / 'child.log').read_text().strip(), 'ordinary child')
            self.assertEqual(observed[0][0], observed[0][1]['value'])
            lock = root / 'session.lock'
            with self.assertRaisesRegex(ValueError, 'control failure'):
                with runner.session_guard(lock):
                    with self.assertRaises(FileExistsError):
                        with runner.session_guard(lock):
                            pass
                    raise ValueError('control failure')
            self.assertFalse(lock.exists())
            with self.assertRaises(KeyboardInterrupt):
                with runner.session_guard(lock):
                    raise KeyboardInterrupt()
            self.assertTrue(lock.exists())  # Inspect possible surviving simulator children before clearing.

    def test_simulation_worker_bodies_and_assertions_are_conserved(self):
        # This is the actual pre-adapter owner. Only the context helper import,
        # its pinned filename, docstring and context-error labels may differ.
        baseline = 'b8a2b610'
        paths = ('Closeout/LocalVM/full38_runtime_worker_v2.py', 'Closeout/LocalVM/stock_runtime_worker_v3.py',
                 'GeneralApiCorrection/capture_windows.py', 'CurrentWindows/LocalVM/runtime_worker_v1.py')

        def normalized(body):
            tree = ast.parse(body)
            if isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
                tree.body.pop(0)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module == 'win_local_process_v1':
                    node.module = 'windows_session_v1'
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    node.value = {'win_local_process_v1.py': 'windows_session_v1.py',
                        'Actual private desktop differs': 'Actual declared rendering context differs',
                        'Actual private desktop context differs': 'Actual declared rendering context differs'}.get(node.value, node.value)
            return ast.dump(tree, include_attributes=False)

        for name in paths:
            old = subprocess.check_output(['git', '-C', str(ROOT), 'show', baseline + ':Tests/Production/' + name])
            self.assertEqual(normalized(old), normalized((ROOT / 'Tests/Production' / name).read_bytes()), name)

    def test_interactive_helpers_only_read_windows_context(self):
        forbidden = {'WTSQueryUserToken', 'CreateProcessAsUserW', 'CreateDesktopW', 'SwitchDesktop',
                     'SetThreadDesktop', 'DuplicateTokenEx', 'ImpersonateLoggedOnUser'}
        for name in (HELPER, RUNNER):
            tree = ast.parse((HERE / 'LocalVM' / name).read_bytes())
            attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
            self.assertFalse(attributes & forbidden)

    def test_preparation_conserves_full_scope_inputs_and_budgets(self):
        import prepare_interactive
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root / 'original'
            original.mkdir()
            legacy.fixture(original)
            cfg = load(original / 'request.json')
            cfg.update(worker_script='Z:/Phase6/scripts/full38_runtime_worker_v2.py',
                       capture_scope=dict(kind='full38'), scene_workers=2,
                       staging_protocol='phase6-guarded-local-staging-v2')
            atomic_json(original / 'request.json', cfg)
            output = root / 'prepared'
            with patch.object(prepare_interactive, 'immutable', side_effect=lambda repo, commit, source:
                              (ROOT / 'Tests/Production' / source).read_bytes()):
                actual = prepare_interactive.prepare(original / 'request.json', output, 'Z:/Fresh',
                    'C:/Python/python.exe', original / 'vm.json', 'a' * 40)
            for name in ('capture_scope', 'minimum_free_bytes', 'source_commit', 'cohort', 'reference_variant'):
                self.assertEqual(actual[name], cfg[name], name)
            self.assertEqual(actual['scene_workers'], 1)
            self.assertEqual(actual['roles']['application'], cfg['roles']['application'])
            self.assertEqual(actual['roles']['sdk'], cfg['roles']['sdk'])
            self.assertEqual(actual['roles']['observer'], cfg['roles']['observer'])
            files = load(output / 'runners.json')['files_sha256']
            self.assertFalse(set(files) & {'win_local_process_v1.py', 'system_user_launcher_v1.py',
                                         'private_desktop_bootstrap_v1.py'})
            self.assertEqual(files, {p.name: sha(p) for p in (output / 'scripts').iterdir()})
            self.assertEqual(load(output / 'preparation.json')['status'], 'prepared-not-executed')
            self.assertFalse((output / 'worker-result.json').exists())
            with self.assertRaises(ValueError):
                prepare_interactive.prepare(original / 'request.json', output, 'Z:/Fresh',
                    'C:/Python/python.exe', original / 'vm.json', 'a' * 40)


if __name__ == '__main__':
    unittest.main()
