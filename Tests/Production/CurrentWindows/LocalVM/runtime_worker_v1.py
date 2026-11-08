"""Run the unchanged current Windows gates on a new, unshown private desktop."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
import zipfile

from win_local_process_v1 import context, sha

request = Path(sys.argv[1])
config = json.loads(request.read_text())
share = request.parent
work = Path(config['work'])
source = Path(config['source'])
output = work / 'qualification-v1'
assert not output.exists()
output.mkdir()
report = dict(status='starting', source_commit=config['source_commit'], context=context(),
              request_sha256=sha(request), worker_sha256=sha(__file__), commands=[],
              cloud_builds_used=False, raw_evidence_uploaded=False, phase6_complete=False,
              started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())


def save():
    text = json.dumps(report, indent=2) + '\n'
    (output / 'worker-status.json').write_text(text)
    temporary = share / (config['name'] + '-worker-status.tmp')
    temporary.write_text(text)
    temporary.replace(share / (config['name'] + '-worker-status.json'))


def run(label, argv):
    log = output / (label + '.log')
    record = dict(label=label, argv=list(map(str, argv)), cwd=str(source), log=str(log),
                  started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    report['commands'].append(record)
    save()
    with log.open('w') as stream:
        process = subprocess.Popen(record['argv'], cwd=source, stdout=stream, stderr=subprocess.STDOUT)
        record['actual_pid'] = process.pid
        save()
        record['actual_exitcode'] = process.wait()
    record['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    record['log_sha256'] = sha(log)
    save()
    return record['actual_exitcode'] == 0


try:
    assert report['context']['session'] == config['active_session']
    assert report['context']['desktop'] == config['desktop']
    assert report['context']['window_station'].lower() == 'winsta0'
    assert report['worker_sha256'] == config['worker_sha256']
    assert sha(share / 'win_local_process_v1.py') == config['helper_sha256']
    os.environ['PATH'] = config['git_directory'] + ';' + str(Path(sys.executable).parent) + ';' + os.environ['PATH']
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ['LIBGL_ALWAYS_SOFTWARE'] = 'true'
    os.environ['GALLIUM_DRIVER'] = 'llvmpipe'
    os.chdir(source)
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == config['source_commit']
    build_record = json.loads((share / 'build-status.json').read_text())
    assert build_record['status'] == 'built-both-current-Windows-configurations-awaiting-runtime-qualification'
    assert build_record['source_commit'] == config['source_commit'] and build_record['owning_sources_unchanged']
    report['build_record_sha256'] = sha(share / 'build-status.json')
    source_before = build_record['source_guard_sha256_lf']
    for name, expected in source_before.items():
        assert hashlib.sha256((source / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == expected, name
    data = Path(config['data'])
    planets = Path(config['planets'])
    report['data_files_sha256'] = {}
    for lock_name, root in (('stock-data', data), ('standard-planets', planets)):
        lock = json.loads((source / ('Tests/Production/' + lock_name + '.lock.json')).read_text())
        for name, expected in lock['data_files'].items():
            actual = sha(root / name)
            checksum = expected['sha256'] if isinstance(expected, dict) else expected
            assert actual == checksum, name
            report['data_files_sha256'][lock_name + '/' + name] = actual
    report['status'] = 'running-current-Windows-gates'
    save()
    all_passed = True
    for configuration in ('Debug', 'Release'):
        runtime = work / ('runtime-' + configuration)
        built = build_record['configuration_results'][configuration]
        assert all(sha(runtime / name) == expected for name, expected in built['runtime_files_sha256'].items())
        common = ['--orbiter', runtime / 'Orbiter.exe', '--data', data, '--planets', planets,
                  '--mesa', config['mesa'], '--configuration', configuration]
        current = output / configuration
        current.mkdir()
        client = current / 'client'
        client_passed = run(configuration + '-client', [sys.executable, '-B', source / 'Tests/Production/Client/run_client.py',
                                                     *common, '--output', client])
        all_passed = all_passed and client_passed
        if client_passed:
            passed = run(configuration + '-surface', [sys.executable, '-B', source / 'Tests/Production/WindowsSurfaceDC/run.py',
                                                      *common, '--baseline', client, '--output', current / 'surface'])
            all_passed = passed and all_passed
        for driver, script, frozen, target in (
            ('cockpit', 'Cockpit/regression.py', 'instruments', 'cockpit'),
            ('controls', 'CockpitControls/current.py', 'controls', 'controls')):
            snapshot = work / (driver + '-binaries-' + configuration)
            for name, expected in built['driver_snapshots'][driver].items():
                assert sha(snapshot / name) == expected
                shutil.copy2(snapshot / name, runtime / 'Modules/Plugin' / name)
            passed = run(configuration + '-' + target, [sys.executable, '-B', source / ('Tests/Production/' + script),
                         *common, '--frozen', Path(config['frozen']) / frozen, '--output', current / target])
            all_passed = passed and all_passed
        # Return each runtime to its fully recorded post-build state.
        for name, expected in built['driver_snapshots']['controls'].items():
            assert sha(runtime / 'Modules/Plugin' / name) == expected
        assert all(sha(runtime / name) == expected for name, expected in built['runtime_files_sha256'].items())
    if all_passed:
        for label, script, folder, extra, option in (
            ('client-comparison', 'Client/compare_client.py', 'client/scene', ['--frozen', source / 'Tests/Production/ClientReference'], '--report'),
            ('cockpit-comparison', 'Cockpit/compare.py', 'cockpit', [], '--output'),
            ('controls-comparison', 'CockpitControls/compare.py', 'controls', [], '--output')):
            passed = run(label, [sys.executable, '-B', source / ('Tests/Production/' + script),
                                '--debug', output / 'Debug' / folder, '--release', output / 'Release' / folder,
                                *extra, option, output / (label + '.json')])
            all_passed = passed and all_passed
    assert all(hashlib.sha256((source / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == expected
               for name, expected in source_before.items())
    report.update(status='passed' if all_passed else 'failed-current-Windows-gates', owning_sources_unchanged=True)
except BaseException as error:
    report.update(status='failed', error=str(error), traceback=traceback.format_exc())
finally:
    save()
    archive = share / (config['name'] + '-observations.zip')
    assert not archive.exists()
    members = {}
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as target:
        for path in sorted(output.rglob('*')):
            if path.is_file() and (path.suffix.lower() in ('.json', '.csv', '.rgba', '.png', '.log', '.txt', '.cfg')
                                  or (path.suffix.lower() == '.scn' and 'Scenarios' in path.parts)):
                name = path.relative_to(output).as_posix()
                target.write(path, name)
                members[name] = sha(path)
    with zipfile.ZipFile(archive) as target:
        assert set(target.namelist()) == set(members)
        assert all(hashlib.sha256(target.read(name)).hexdigest() == expected for name, expected in members.items())
    preservation = dict(status='preserved-and-rehashed', archive_sha256=sha(archive),
                        archive_bytes=archive.stat().st_size, files_sha256=members,
                        scope='Local current-source observations; application/SDK and scientific data remain in their guarded local build directories.')
    (share / (config['name'] + '-preservation.json')).write_text(json.dumps(preservation, indent=2) + '\n')
sys.exit(0 if report['status'] == 'passed' else 1)
