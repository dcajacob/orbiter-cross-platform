"""Run one pinned qualification worker from the existing non-elevated desktop.

Start this script in the Windows VM as the signed-in user. It uses ordinary
subprocess inheritance, waits for the actual child, and retains its evidence.
"""
import json
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from windows_session_v1 import context, elevated, machine_uuid, require, sha, start_identity

PROTOCOL = 'phase6-interactive-windows-launch-v1'
LEGACY = {'win_local_process_v1.py', 'system_user_launcher_v1.py', 'private_desktop_bootstrap_v1.py'}


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


@contextmanager
def session_guard(path):
    stream = path.open('x')
    interrupted = False
    try:
        yield stream
    except BaseException as error:
        interrupted = not isinstance(error, Exception)
        raise
    finally:
        stream.close()
        if not interrupted:
            path.unlink()


def observe_child(argv, cwd, log, identity, on_start):
    """Keep the real child handle through its exit; also exercised by POSIX controls."""
    with Path(log).open('xb') as stream:
        process = subprocess.Popen(argv, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        try:
            on_start(process.pid, identity(process))
            return process.wait()
        except BaseException:
            # Reap this directly owned worker; never signal unrelated processes.
            if process.poll() is None:
                process.terminate()
            process.wait()
            raise


def main():
    require(sys.platform == 'win32', 'Launch inside the local Windows VM as the signed-in user')
    request = Path(sys.argv[1]).resolve()
    cfg = json.loads(request.read_text())
    launch = cfg['interactive_launch']
    require(launch['protocol'] == PROTOCOL and len(launch['nonce']) == 32, 'Explicit interactive launch required')
    actual_context = context()
    require(actual_context == dict(session=cfg['active_session'], window_station='WinSta0', desktop='Default') and
            cfg['desktop'] == 'Default' and actual_context['session'] > 0 and not elevated(),
            'Use the existing visible, non-elevated Windows user session')
    actual_machine_uuid = machine_uuid()
    require(actual_machine_uuid == launch['domain_uuid'], 'Actual Windows machine UUID differs from the declared local VM')
    require(request == Path(cfg['request_path']).resolve() and
            Path(sys.executable).resolve() == Path(launch['python']).resolve(), 'Actual request/Python path differs')
    root = request.parent
    manifest = root / 'runners.json'
    runners = json.loads(manifest.read_text())
    files = runners['files_sha256']
    scripts = root / 'scripts'
    require(set(path.name for path in scripts.iterdir()) == set(files) and not set(files) & LEGACY,
            'Exact ordinary-session script closure required')
    require(runners['commit'] == cfg['roles']['runner']['commit'] and
            sha(manifest) == cfg['roles']['runner']['manifest_sha256'] and
            cfg['bootstrap_sha256'] == files[Path(__file__).name] and
            Path(cfg['bootstrap_script']).resolve() == Path(__file__).resolve() and
            Path(cfg['worker_script']).parent.resolve() == scripts.resolve() and
            cfg['worker_sha256'] == files[Path(cfg['worker_script']).name], 'Pinned runner/worker manifest differs')
    result_path = root / launch['worker_result']
    require(result_path.parent == root and result_path.suffix == '.json' and not result_path.exists(),
            'Fresh local worker result required')
    guards = {request: sha(request), manifest: sha(manifest)}
    guards.update({scripts / name: digest for name, digest in files.items()})
    require(all(sha(path) == digest for path, digest in guards.items()), 'Runner script bytes changed before launch')
    require(not (root / 'interactive-result.json').exists(), 'An interactive request cannot be relaunched')
    # Serialise work on the shared visible desktop, including separate packages.
    session_lock = Path(tempfile.gettempdir()) / ('orbiter-qualification-session-' + str(cfg['active_session']) + '.lock')
    claimed = False
    started = time.monotonic_ns()
    report = dict(protocol=PROTOCOL, nonce=launch['nonce'], request_sha256=guards[request],
        context=actual_context, platform=sys.platform, elevated=False, actual_runner_pid=os.getpid(),
        actual_machine_uuid=actual_machine_uuid,
        runner_sha256=sha(__file__), helper_sha256=sha(Path(__file__).with_name('windows_session_v1.py')),
        worker_sha256=cfg['worker_sha256'], scripts_sha256=files, python=str(Path(sys.executable)),
        worker_argv=['-B', cfg['worker_script'], cfg['request_path']])
    with session_guard(session_lock) as lock:
        try:
            lock.write(json.dumps(dict(pid=os.getpid(), request=str(request), nonce=launch['nonce'])))
            lock.flush()
            with (root / 'interactive-claimed.json').open('x') as claim:
                json.dump(dict(nonce=launch['nonce'], request_sha256=guards[request]), claim)
            claimed = True

            def on_start(pid, identity):
                report.update(status='started-interactive-windows-worker', actual_worker_pid=pid,
                              worker_start_identity=identity)
                save(root / 'interactive-started.json', report)
                print('Started qualification worker', pid, 'on the existing Windows desktop.', flush=True)

            code = observe_child([sys.executable, *report['worker_argv']], cfg['source'],
                                 root / 'interactive-worker.log', start_identity, on_start)
            report.update(actual_worker_returncode=code, elapsed_wall_ns=time.monotonic_ns() - started)
            require(code == 0, 'Qualification worker failed; inspect interactive-worker.log')
            require(all(sha(path) == digest for path, digest in guards.items()), 'Runner/request changed during execution')
            worker = json.loads(result_path.read_text())
            require(worker['request_sha256'] == guards[request] and worker['context'] == actual_context,
                    'Actual worker result belongs to another request/session')
            require(not worker['status'].startswith(('failed', 'running', 'starting')),
                    'Worker did not retain a completed result')
            report.update(status='completed-interactive-windows-worker', inputs_unchanged=True,
                          worker_result_sha256=sha(result_path), worker_log_sha256=sha(root / 'interactive-worker.log'))
        except BaseException as error:
            report.update(status='failed', error=str(error), elapsed_wall_ns=time.monotonic_ns() - started)
            raise
        finally:
            if claimed:
                save(root / 'interactive-result.json', report)
    print('Worker finished. Independent simulation and launch audits are still required.', flush=True)


if __name__ == '__main__':
    main()
