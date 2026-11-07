#!/usr/bin/env python3
"""Build matching local Windows packages without advancing an evidence owner.

This consolidates the historical local build scripts. All machine-specific paths
come from a hashed request; source, dependencies and accepted packages stay put.
"""
import argparse
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


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    args = parser.parse_args()
    require(sys.platform == 'win32', 'Actual local Windows build required')
    cfg = json.loads(args.request.read_text())
    require(cfg['protocol'] == 'phase6-current-Windows-build-v1', 'Unknown build request')
    work = Path(cfg['work']); source = work / 'source'
    export = Path(cfg['export']); bundle = Path(cfg['bundle'])
    require(not work.exists() and not export.exists(), 'Fresh build and export required')
    protected = [Path(cfg[n]).resolve() for n in
                 ('seed_source', 'dependency_source_root', 'renderer_archives', 'compiler_environment')]
    require(all(not work.resolve().is_relative_to(p) and not p.is_relative_to(work.resolve())
                for p in protected), 'Build overlaps a protected input')
    reserve = cfg['minimum_free_bytes']
    require(type(reserve) is int and reserve >= 8 * 1024**3 and
            shutil.disk_usage(work.parent).free >= reserve + cfg['estimated_build_bytes'],
            'Insufficient declared local build capacity')
    require(sha(bundle) == cfg['bundle_sha256'], 'Candidate bundle changed')
    require(len(cfg['source_commit']) == 40 and cfg['jobs'] in (1, 2),
            'Fixed source and at most two compiler jobs required')
    work.mkdir(); export.mkdir()
    report = dict(protocol=cfg['protocol'], status='preparing', source_commit=cfg['source_commit'],
                  request_sha256=sha(args.request), builder_sha256=sha(__file__),
                  source=str(source), work=str(work), configurations={}, commands=[],
                  initial_free_bytes=shutil.disk_usage(work).free, minimum_free_bytes=reserve,
                  cloud_builds_used=False, raw_evidence_uploaded=False, phase6_complete=False)

    def save():
        body = json.dumps(report, indent=2) + '\n'
        for root in (work, export):
            tmp = root / 'build.json.tmp'; tmp.write_text(body); tmp.replace(root / 'build.json')

    def run(label, argv, env=None, cwd=None):
        require(shutil.disk_usage(work).free >= reserve, 'Local build reserve exhausted')
        log = work / (label + '.log')
        item = dict(label=label, argv=list(map(str, argv)), cwd=str(cwd or work), log=str(log),
                    started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        report['commands'].append(item); save()
        with log.open('w') as stream:
            child = subprocess.Popen(item['argv'], cwd=cwd or work, env=env,
                                     stdout=stream, stderr=subprocess.STDOUT)
            item['actual_pid'] = child.pid; save()
            item['actual_returncode'] = child.wait()
        item.update(log_sha256=sha(log),
                    finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        save()
        require(item['actual_returncode'] == 0,
                label + ': ' + log.read_text(errors='replace')[-5000:])
        print(label, 'passed', flush=True)

    git = cfg['git']; cmake = Path(cfg['cmake']); ninja = Path(cfg['ninja'])
    try:
        run('clone-source', [git, 'clone', '--shared', '--no-checkout', cfg['seed_source'], source])
        run('verify-bundle', [git, '-C', source, 'bundle', 'verify', bundle])
        run('fetch-source', [git, '-C', source, 'fetch', bundle, cfg['bundle_ref']])
        run('checkout-source', [git, '-C', source, 'checkout', '--detach', cfg['source_commit']])
        require(subprocess.check_output([git, '-C', source, 'rev-parse', 'HEAD'], text=True).strip()
                == cfg['source_commit'], 'Actual checked out source differs')
        names = subprocess.check_output([git, '-C', source, 'ls-tree', '-r', '--name-only', 'HEAD'], text=True).splitlines()
        guards = {n: hashlib.sha256((source/n).read_bytes().replace(b'\r\n', b'\n')).hexdigest() for n in names}
        report['source_guard_sha256_lf'] = guards
        deps = json.loads((source/'Tests/Production/dependencies.lock.json').read_text())['dependencies']
        dependency_root = work/'dependencies'; dependency_root.mkdir()
        for name, identity in deps.items():
            original = Path(cfg['dependency_source_root'])/(name.lower()+'-src')
            require(subprocess.check_output([git, '-C', original, 'rev-parse', 'HEAD'], text=True).strip()
                    == identity['commit'], 'Pinned local dependency differs: '+name)
            target = dependency_root/original.name
            run('clone-'+name, [git, 'clone', '--shared', '--no-checkout', original, target])
            run('checkout-'+name, [git, '-C', target, 'checkout', '--detach', identity['commit']])
            run('origin-'+name, [git, '-C', target, 'remote', 'set-url', 'origin', identity['repository']])
        shutil.copyfile(source/'Extern/imgui/imconfig.h', dependency_root/'imgui-src/imconfig.h')
        renderer_sources = {}; renderer = work/'renderer-dependencies'; renderer.mkdir()
        lock = json.loads((source/'OVP/OGLClient/dependencies.lock.json').read_text())
        report['renderer_archives_sha256'] = {}
        for name in ('glm', 'freetype', 'soil2', 'nanovg', 'libnsbmp', 'imgui', 'zlib'):
            archive = Path(cfg['renderer_archives'])/(name+'.zip')
            require(sha(archive) == lock[name]['sha256'], 'Pinned renderer archive differs: '+name)
            report['renderer_archives_sha256'][str(archive)] = sha(archive)
            target = renderer/name; target.mkdir()
            with zipfile.ZipFile(archive) as packaged:
                require(all(not Path(n).is_absolute() and '..' not in Path(n).parts
                            for n in packaged.namelist()), 'Unsafe dependency archive')
                packaged.extractall(target)
            children = list(target.iterdir())
            require(len(children) == 1 and children[0].is_dir(), 'Unexpected renderer archive root')
            renderer_sources[name] = children[0]
        environment = {n.upper(): v for n, v in os.environ.items()}
        cmd = Path(os.environ['SystemRoot'])/'System32/cmd.exe'
        output = subprocess.check_output([str(cmd), '/d', '/c', cfg['compiler_environment']], text=True)
        for line in output.splitlines():
            name, sep, value = line.partition('=')
            if sep and name and not name.startswith('='):
                environment[name.upper()] = value
        environment.update(PYTHONDONTWRITEBYTECODE='1', DXSDK_DIR=cfg['dxsdk'])
        temporary = work/'temporary'; temporary.mkdir()
        environment.update(TEMP=str(temporary), TMP=str(temporary))
        environment['PATH'] = ';'.join(map(str, (Path(git).parent, Path(sys.executable).parent,
                                      cmake.parent, ninja.parent)))+';'+environment['PATH']
        report['tool_environment'] = {n: environment.get(n) for n in
                                     ('VCTOOLSVERSION', 'WINDOWSSDKVERSION', 'VSCMD_VER')}
        for configuration in ('Debug', 'Release'):
            report.update(status='building', active_configuration=configuration); save()
            build = work/('build-'+configuration)
            flags = ['-DCMAKE_BUILD_TYPE='+configuration, '-DCMAKE_C_COMPILER=cl', '-DCMAKE_CXX_COMPILER=cl',
                     '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON', '-DORBITER_BUILD_D3D9CLIENT=ON',
                     '-DORBITER_BUILD_XRSOUND=OFF', '-DORBITER_MAKE_DOC=OFF', '-DORBITER_MAKE_TESTS=ON',
                     '-DORBITER_PORTABLE_REFERENCE_CAPTURE=ON', '-DORBITER_PRODUCTION_REFERENCE_CAPTURE=ON',
                     '-DFETCHCONTENT_FULLY_DISCONNECTED=ON', '-DDXSDK_DIR:PATH='+cfg['dxsdk']]
            flags += ['-DFETCHCONTENT_SOURCE_DIR_'+name.upper()+'='+str(dependency_root/(name.lower()+'-src')) for name in deps]
            run(configuration+'-configure', [cmake, '-S', source, '-B', build, '-G', 'Ninja', *flags], environment, source)
            run(configuration+'-build', [cmake, '--build', build, '--parallel', cfg['jobs']], environment, source)
            listing = subprocess.check_output([str(cmake.parent/'ctest.exe'), '--test-dir', str(build), '--show-only=json-v1'], env=environment, text=True)
            tests = json.loads(listing); require(tests['tests'], 'No existing Windows tests registered')
            inventory = work/(configuration+'-registered-tests.json'); inventory.write_text(listing)
            junit = work/(configuration+'-ctest.xml')
            run(configuration+'-ctest', [cmake.parent/'ctest.exe', '--test-dir', build,
                '--output-on-failure', '--output-junit', junit], environment, source)
            run(configuration+'-metadata', [sys.executable, '-B', source/'Tests/Production/build_metadata.py', '--build', build], environment, source)
            archive = work/('runtime-'+configuration+'.zip')
            run(configuration+'-package', [sys.executable, '-B', source/'Tests/Production/package_test_runtime.py', '--build', build, '--output', archive], environment, source)
            runtime = work/('runtime-'+configuration)
            with zipfile.ZipFile(archive) as packaged:
                packaged.extractall(runtime)
            run(configuration+'-verify-runtime', [sys.executable, '-B', source/'Tests/Production/verify_test_runtime.py', '--runtime', runtime, '--source', cfg['source_commit']], environment, source)
            client = work/('client-'+configuration)
            flags = ['-DCMAKE_BUILD_TYPE='+configuration, '-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
                     '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON', '-DORBITER_TEST_RUNTIME='+str(runtime),
                     '-DDXSDK_DIR='+cfg['dxsdk'], '-DFETCHCONTENT_FULLY_DISCONNECTED=ON']
            flags += ['-DFETCHCONTENT_SOURCE_DIR_'+n.upper()+'='+str(p) for n, p in renderer_sources.items()]
            run(configuration+'-client-configure', [cmake, '-S', source/'OVP/OGLClient', '-B', client, '-G', 'Ninja', *flags], environment, source)
            run(configuration+'-client-build', [cmake, '--build', client, '--target', 'OGLClient', '--parallel', cfg['jobs']], environment, source)
            snapshots = {}
            for name, relative in (('behavior', 'BehaviorBuild'), ('cockpit', 'Cockpit'),
                                   ('controls', 'CockpitControls'), ('surface', 'WindowsSurfaceDC'),
                                   ('attachment', 'AttachmentTeardownWindows')):
                target = work/(name+'-driver-'+configuration)
                run(configuration+'-'+name+'-configure', [cmake, '-S', source/'Tests/Production'/relative,
                    '-B', target, '-G', 'Ninja', '-DCMAKE_BUILD_TYPE='+configuration,
                    '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON', '-DORBITER_TEST_RUNTIME='+str(runtime),
                    '-DORBITER_SOURCE_ROOT='+str(source)], environment, source)
                run(configuration+'-'+name+'-build', [cmake, '--build', target, '--parallel', cfg['jobs']], environment, source)
                if name in ('cockpit', 'controls'):
                    snapshot = work/(name+'-binaries-'+configuration); snapshot.mkdir()
                    for p in (runtime/'Modules/Plugin').glob('ProductionCockpitDriver.*'):
                        shutil.copy2(p, snapshot/p.name)
                    snapshots[name] = {p.name: sha(p) for p in snapshot.iterdir() if p.is_file()}
                elif name == 'attachment':
                    for p in (target/'bin').glob('ProductionAttachmentTeardownDriver.*'):
                        shutil.copy2(p, runtime/'Modules/Plugin'/p.name)
            report['configurations'][configuration] = dict(status='built', runtime=str(runtime), build=str(build),
                sdk_manifest_sha256=sha(runtime/'test-runtime.json'), build_inputs_sha256=sha(build/'build-inputs.json'),
                driver_snapshots=snapshots, registered_tests=len(tests['tests']),
                tests_inventory_sha256=sha(inventory), ctest_xml_sha256=sha(junit),
                runtime_files_sha256={p.relative_to(runtime).as_posix(): sha(p) for p in runtime.rglob('*') if p.is_file()})
            save()
        require(all(hashlib.sha256((source/n).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == value
                    for n, value in guards.items()), 'Owning Windows source changed')
        require(all(sha(p) == value for p, value in report['renderer_archives_sha256'].items()), 'Renderer input changed')
        report.update(status='built-both-current-Windows-configurations-awaiting-runtime-qualification',
                      owning_sources_unchanged=True, final_free_bytes=shutil.disk_usage(work).free)
    except BaseException as error:
        report.update(status='failed', error=str(error), traceback=traceback.format_exc())
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
