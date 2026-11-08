#!/usr/bin/env python3
"""Prepare a fresh ordinary-session package while conserving a qualification request."""
import argparse
import copy
import hashlib
import json
from pathlib import Path, PureWindowsPath
import subprocess
import uuid

from contracts import ROOT, atomic_json, load, require, sha
from interactive_launch import PROTOCOL, RUNNER, HELPER, validate
from LocalVM import runtime_descriptor_v2, runtime_descriptor_v3

WORKERS = {
    'full38_runtime_worker_v2.py': 'Closeout/LocalVM/full38_runtime_worker_v2.py',
    'stock_runtime_worker_v3.py': 'Closeout/LocalVM/stock_runtime_worker_v3.py',
    'capture_api.py': 'GeneralApiCorrection/capture_windows.py',
    'runtime_worker_v1.py': 'CurrentWindows/LocalVM/runtime_worker_v1.py',
}
COMMON = {name: 'Closeout/LocalVM/' + name for name in (RUNNER, HELPER, 'runtime_descriptor_v2.py')}


def immutable(repository, commit, source):
    return subprocess.check_output(['git', '-C', str(repository), 'show', commit + ':Tests/Production/' + source])


def prepare(template, output, guest_root, python, vm_path, runner_commit, repository=ROOT):
    require(not output.exists(), 'Fresh interactive package directory required')
    original = load(template)
    cfg = copy.deepcopy(original)
    require('interactive_launch' not in cfg, 'Prepare from an original qualification request, never a previously claimed job')
    guest = runtime_descriptor_v2.windows_path(guest_root)
    interpreter = runtime_descriptor_v2.windows_path(python)
    worker = PureWindowsPath(cfg['worker_script']).name
    require(worker in WORKERS, 'Unsupported qualification worker; do not substitute or shorten its test scope')
    sources = dict(COMMON, **{worker: WORKERS[worker]})
    if cfg['transport_protocol'] == runtime_descriptor_v3.PROTOCOL:
        sources['runtime_descriptor_v3.py'] = 'Closeout/LocalVM/runtime_descriptor_v3.py'
    if worker in ('full38_runtime_worker_v2.py', 'stock_runtime_worker_v3.py'):
        sources['static_binary_link_staging_v2.py'] = 'Closeout/LocalVM/static_binary_link_staging_v2.py'
    if worker == 'stock_runtime_worker_v3.py':
        sources['current_stock.py'] = 'CurrentWindows/stock.py'
    if worker == 'capture_api.py':
        sources['static_binary_link_staging_v1.py'] = 'RemainingStockPersistence/LocalVM/static_binary_link_staging_v1.py'
    blobs = {name: immutable(repository, runner_commit, source) for name, source in sources.items()}
    hashes = {name: hashlib.sha256(body).hexdigest() for name, body in blobs.items()}
    require(b'from windows_session_v1 import ' in blobs[worker], 'Worker must use the read-only session helper')
    vm = load(vm_path)
    require(vm['hypervisor'] == 'libvirt/kvm' and vm['guest_os_id'] == 'mswindows', 'Explicit local Windows VM required')
    nonce = uuid.uuid4().hex
    cfg.update(name='interactive-' + nonce, desktop='Default', request_path=str(guest / 'request.json'),
               worker_script=str(guest / 'scripts' / worker), worker_sha256=hashes[worker],
               bootstrap_script=str(guest / 'scripts' / RUNNER), bootstrap_sha256=hashes[RUNNER],
               output=str(PureWindowsPath(cfg['output']).parent / ('Interactive-' + nonce)),
               export=str(guest / 'export'))
    cfg['roots'].update(share=str(guest), output=cfg['output'])
    witness = ('Orbiter ordinary-session package ' + nonce + '\n').encode()
    cfg['share_witness'] = dict(path='share-witness.txt', sha256=hashlib.sha256(witness).hexdigest())
    if worker == 'full38_runtime_worker_v2.py':
        cfg['scene_workers'] = 1
    if 'helper_sha256' in cfg:
        cfg['helper_sha256'] = hashes[HELPER]
    runners = dict(commit=runner_commit, files_sha256=hashes, source_paths=sources,
                   launch_protocol=PROTOCOL)
    manifest_bytes = (json.dumps(runners, indent=2) + '\n').encode()
    cfg['roles']['runner'] = dict(commit=runner_commit, manifest_path=str(guest / 'runners.json'),
                                 manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest())
    cfg['interactive_launch'] = dict(protocol=PROTOCOL, nonce=nonce, python=str(interpreter),
        worker_result=cfg['name'] + '-worker-status.json' if worker == 'runtime_worker_v1.py' else 'worker-result.json',
        domain_name=vm['domain_name'], domain_uuid=vm['domain_uuid'])
    # A finite configuration diff keeps scopes, paired inputs, thresholds,
    # packages, source commits and capacity reserves exactly as requested.
    allowed = {'name', 'desktop', 'request_path', 'worker_script', 'worker_sha256', 'bootstrap_script',
               'bootstrap_sha256', 'output', 'export', 'roots', 'roles', 'share_witness', 'scene_workers',
               'helper_sha256', 'interactive_launch'}
    require(all(cfg.get(key) == value for key, value in original.items() if key not in allowed),
            'Qualification settings changed beyond the launch adapter')
    require(all(cfg['roots'][key] == value for key, value in original['roots'].items() if key not in ('share', 'output')) and
            all(cfg['roles'][key] == value for key, value in original['roles'].items() if key != 'runner'),
            'Protected runtime/source/data roles changed')
    descriptor = runtime_descriptor_v3 if cfg['transport_protocol'] == runtime_descriptor_v3.PROTOCOL else runtime_descriptor_v2
    descriptor.validate(cfg)
    validate(cfg)
    # Avoid cmd.exe expansion or metacharacters in this generated convenience entry point.
    arguments = [str(interpreter), cfg['bootstrap_script'], cfg['request_path']]
    require(all(not any(char in arg for char in '\r\n"%!&|<>^') for arg in arguments), 'Unsafe command-file path')
    output.mkdir(parents=True)
    (output / 'scripts').mkdir()
    for name, body in blobs.items():
        (output / 'scripts' / name).write_bytes(body)
    (output / 'runners.json').write_bytes(manifest_bytes)
    (output / 'share-witness.txt').write_bytes(witness)
    atomic_json(output / 'request.json', cfg)
    atomic_json(output / 'vm.json', vm)
    atomic_json(output / 'template-request.json', original)
    atomic_json(output / 'preparation.json', dict(status='prepared-not-executed', template=str(template),
        template_sha256=sha(template), request_sha256=sha(output / 'request.json'), runner_commit=runner_commit,
        scripts_sha256=hashes, scope_and_acceptance_settings_unchanged=True, phase6_complete=False))
    command = '@echo off\r\nsetlocal DisableDelayedExpansion\r\n"' + arguments[0] + '" -B "' + arguments[1] + '" "' + arguments[2] + '"\r\nexit /b %ERRORLEVEL%\r\n'
    (output / 'run.cmd').write_bytes(command.encode())
    return cfg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('template', 'output', 'vm'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--guest-root', required=True)
    parser.add_argument('--python', required=True)
    parser.add_argument('--runner-commit', required=True)
    args = parser.parse_args()
    prepare(args.template, args.output, args.guest_root, args.python, args.vm, args.runner_commit)
    print('Prepared', args.output / 'run.cmd', '; launch it as the signed-in Windows VM user.')


if __name__ == '__main__':
    main()
