#!/usr/bin/env python3
"""Run the versioned conic fixture against retained current-Windows unit libraries."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    require(sys.platform == 'win32' and len(sys.argv) == 2, 'Actual Windows request required')
    request = Path(sys.argv[1]); cfg = json.loads(request.read_text())
    require(cfg['variant'] == 'orbit-geometry-production-state-initialization-v1', 'Unknown fixture variant')
    work = Path(cfg['sdk_work']); output = Path(cfg['output']); export = Path(cfg['export'])
    source = Path(cfg['test_source'])
    require(not output.exists() and not export.exists() and sha(source) == cfg['test_sha256'],
            'Fresh output and exact versioned fixture required')
    built = json.loads((work/'build.json').read_text())
    require(built['source_commit'] == cfg['application_source_commit'] and built['owning_sources_unchanged'],
            'Actual retained application source differs')
    require(shutil.disk_usage(output.parent).free >= 8*1024**3, 'Windows capacity reserve unavailable')
    output.mkdir(); export.mkdir()
    record = dict(status='running', variant=cfg['variant'], request_sha256=sha(request),
                  collector_sha256=sha(__file__), test_sha256=sha(source),
                  application_source_commit=built['source_commit'], configurations={}, commands=[],
                  production_changed=False, complete_gate_credit=False)

    def save():
        body = json.dumps(record, indent=2)+'\n'
        (output/'verification.json').write_text(body); (export/'verification.json').write_text(body)

    def run(label, argv, environment):
        entry = dict(label=label, argv=list(map(str, argv))); record['commands'].append(entry); save()
        with (output/(label+'.log')).open('w') as log:
            child = subprocess.Popen(entry['argv'], cwd=output, env=environment,
                                     stdout=log, stderr=subprocess.STDOUT)
            entry['actual_pid'] = child.pid; save(); entry['returncode'] = child.wait()
        entry['log_sha256'] = sha(output/(label+'.log'))
        shutil.copy2(output/(label+'.log'), export/(label+'.log')); save()
        require(entry['returncode'] == 0, label+' failed; retain actual log')

    try:
        cmd = Path(os.environ['SystemRoot'])/'System32/cmd.exe'
        text = subprocess.check_output([str(cmd), '/d', '/c', cfg['compiler_environment']], text=True)
        env = {name.upper(): value for name, value in os.environ.items()}
        for line in text.splitlines():
            name, separator, value = line.partition('=')
            if separator and name and not name.startswith('='): env[name.upper()] = value
        env['PATH'] = str(Path(cfg['cmake']).parent)+';'+str(Path(cfg['ninja']).parent)+';'+env['PATH']
        for configuration in ('Debug', 'Release'):
            build = Path(built['configurations'][configuration]['build'])
            libraries = list(build.rglob('orbiter_production_boundary.lib'))
            require(len(libraries) == 1, 'Unique actual retained boundary import library required')
            library = libraries[0]; dll = library.with_suffix('.dll')
            require(dll.is_file(), 'Actual retained production boundary DLL missing')
            guards = {str(p): sha(p) for p in (library, dll, source)}
            fixture = output/configuration; fixture.mkdir()
            root = Path(built['source'])
            quote = lambda path: json.dumps(str(path).replace('\\', '/'))
            body = '\n'.join([
                'cmake_minimum_required(VERSION 3.19)', 'project(CorrectedExistingConicFixture LANGUAGES CXX)',
                'add_library(retained_boundary SHARED IMPORTED)',
                'set_target_properties(retained_boundary PROPERTIES IMPORTED_IMPLIB '+quote(library)+' IMPORTED_LOCATION '+quote(dll)+')',
                'add_executable(corrected_orbit '+quote(source)+')',
                'target_compile_features(corrected_orbit PRIVATE cxx_std_17)',
                'target_compile_definitions(corrected_orbit PRIVATE NOMINMAX ORBITER_PRODUCTION_SHARED ORBITER_NATIVE_BUILD_CONFIGURATION=\\"'+configuration+'\\")',
                'target_include_directories(corrected_orbit PRIVATE '+quote(root/'Src/Orbiter')+' '+quote(root/'Orbitersdk/include')+')',
                'target_link_libraries(corrected_orbit PRIVATE retained_boundary)', ''])
            (fixture/'CMakeLists.txt').write_text(body)
            run(configuration+'-configure', [cfg['cmake'], '-S', fixture, '-B', fixture/'build', '-G', 'Ninja',
                '-DCMAKE_BUILD_TYPE='+configuration, '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON'], env)
            run(configuration+'-build', [cfg['cmake'], '--build', fixture/'build', '--parallel', '2'], env)
            current = dict(env, PATH=str(dll.parent)+';'+env['PATH'])
            run(configuration+'-run', [fixture/'build/corrected_orbit.exe'], current)
            require(all(sha(p) == value for p, value in guards.items()), 'Retained production/fixture bytes changed')
            record['configurations'][configuration] = dict(status='passed-corrected-existing-fixture',
                projections=48, guarded_files_sha256=guards, executable_sha256=sha(fixture/'build/corrected_orbit.exe'))
            save()
        record['status'] = 'passed-current-Windows-corrected-existing-conic-fixture'
    except BaseException as error:
        record.update(status='failed', error=str(error)); raise
    finally:
        save()


if __name__ == '__main__':
    main()
