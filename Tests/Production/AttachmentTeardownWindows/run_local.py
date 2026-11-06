#!/usr/bin/env python3
"""Run source-bound paused Windows worlds through normal launchpad cleanup."""
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
import zipfile


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect(folder, worlds, math_profile, expected_modules):
    require = lambda value, message: None if value else (_ for _ in ()).throw(ValueError(message))
    require((folder / 'attachment-completed-worlds.txt').read_text().strip() == str(worlds), 'Normal world completions missing')
    require((folder / 'attachment-driver-unloaded.txt').read_text().strip() == str(worlds), 'Actual driver did not finish unloading')
    require(not (folder / 'attachment-failure.txt').exists(), 'Actual paused attachment driver failed')
    profile = (folder / 'attachment-math.txt').read_text().strip()
    require(profile in ('fma3', 'sse2') and (math_profile != 'sse2' or profile == 'sse2'), 'Actual CRT profile differs')
    rows = list(csv.DictReader((folder / 'attachment-vessels.csv').open()))
    require(len(rows) == worlds * 60 * 3, 'Incomplete actual paused world state sequence')
    names = {'ISS': 'ProjectAlpha_ISS', 'STS-101': 'Atlantis', 'Leonardo': 'Leonardo_mplm'}
    groups = {}
    for row in rows:
        key = int(row['world']), int(row['frame'])
        groups.setdefault(key, {})
        require(row['object'] not in groups[key], 'Duplicate paused vessel observation')
        groups[key][row['object']] = row['class']
        require(float(row['seconds']) == 0 and all(row[name] == '1' for name in ('paused', 'iss_dock', 'shuttle_child', 'payload_parent')),
                'Actual world advanced or lost a reciprocal link')
        require(all(math.isfinite(float(value)) for key, value in row.items() if key not in ('object', 'class')), 'Nonfinite actual lifetime state')
    require(set(groups) == {(world, frame) for world in range(1, worlds+1) for frame in range(1, 61)} and
            all(roster == names for roster in groups.values()), 'Complete original paused roster differs')
    events = list(csv.DictReader((folder / 'attachment-events.csv').open()))
    starts = [row for row in events if row['event'] == 'start-pause-request']
    ends = [row for row in events if row['event'] == 'normal-world-cleanup-complete']
    selections = [row for row in events if row['event'] == 'selected-original']
    require([int(row['world']) for row in starts] == list(range(1, worlds+1)) and all(row['frame'] == '0' for row in starts), 'Actual world-start sequence differs')
    require([int(row['world']) for row in ends] == list(range(1, worlds+1)) and all(row['frame'] == '60' for row in ends), 'Actual cleanup sequence differs')
    require(len(selections) == worlds-1 and all(row['detail'] == 'Space Shuttle Atlantis/Atlantis ISS Resupply.scn' for row in selections), 'Actual original launchpad selections differ')
    log = (folder / 'Orbiter.log').read_text(errors='replace')
    require(log.count('**** Closing simulation session') == worlds and 'Fast process shutdown' not in log and 'Respawning Orbiter' not in log,
            'Normal world cleanup was bypassed')
    require(not any(text in log for text in ('Could not find a module', 'Assertion failed', 'Lua error:', 'LuaCall (')), 'Actual runtime reported a failure')
    system = Path(os.environ['SystemRoot']).resolve()
    loaded = {}
    for world in range(1, worlds+1):
        part = folder / ('attachment-world-' + str(world))
        life = json.loads((part / 'graphics-lifecycle.json').read_text())
        require(life == dict(rendered_frames=60, successful_presents=60, context_deleted=True), 'Actual per-world graphics lifetime differs')
        renderer = json.loads((part / 'renderer-info.json').read_text())
        require('llvmpipe' in renderer['renderer'].lower() and renderer['client_width'] == 1280 and renderer['client_height'] == 720,
                'Actual renderer or viewport differs')
        visual = list(csv.DictReader((part / 'visual-events.csv').open()))
        for event in ('register', 'unregister'):
            require(set(names) <= {row['object'] for row in visual if row['event'] == event}, 'Original vessel visual lifetime incomplete')
        seen = set()
        for line in (folder / ('attachment-loaded-modules-world-' + str(world) + '.txt')).read_text().splitlines():
            path = Path(line).resolve()
            if path.suffix.lower() != '.dll' and path.name.lower() != 'orbiter.exe':
                continue
            seen.add(path.name.lower())
            if system in path.parents:
                continue
            require(folder.resolve() in path.parents and path.name.lower() in expected_modules, 'Unrecorded external application DLL')
            require(sha(path) in expected_modules[path.name.lower()], 'Actual application or provider DLL bytes differ')
            loaded[str(path)] = sha(path)
        require({'orbiter.exe', 'oglclient.dll', 'opengl32.dll', 'libgallium_wgl.dll', 'atlantis.dll', 'productionattachmentteardowndriver.dll'} <= seen,
                'Actual current application, renderer or lifetime driver was not loaded')
    for name in ('graphics-errors.txt', 'graphics-fault.txt'):
        path = folder / name
        require(not path.exists() or not path.read_text(errors='replace').strip(), 'Actual graphics diagnostics reported a failure')
    return dict(status='passed', worlds=worlds, actual_math=profile, paused_vessel_rows=len(rows), successful_presents=worlds*60,
                normal_cleanup_events=len(ends), original_launchpad_restarts=len(selections), loaded_modules_sha256=loaded)


def main():
    request = Path(sys.argv[1])
    cfg = json.loads(request.read_text())
    sys.path.insert(0, str(request.parent))
    from win_local_process_v1 import context
    source = Path(cfg['source'])
    sys.path[:0] = [str(source / 'Tests/Production'), str(source / 'Tests/Production/Client'), str(source / 'Tests/Production/RemainingStock')]
    from behavior_suite import link_or_copy
    from run_client import mesa_files
    import data_inputs
    import inputs
    work = Path(cfg['work'])
    output = work / cfg['name']
    assert not output.exists()
    output.mkdir()
    report = dict(status='starting', context=context(), source_commit=cfg['source_commit'], runner_commit=cfg['runner_commit'],
                  request_sha256=sha(request), worker_sha256=sha(__file__), actual_processes=[], results={},
                  native_admission_qualified=False, phase6_complete=False, cloud_builds_used=False, raw_evidence_uploaded=False)

    def save():
        text = json.dumps(report, indent=2) + '\n'
        (output / 'worker-status.json').write_text(text)
        temporary = request.parent / (cfg['name'] + '-worker-status.tmp')
        temporary.write_text(text)
        temporary.replace(request.parent / (cfg['name'] + '-worker-status.json'))

    try:
        assert report['context'] == dict(session=cfg['active_session'], window_station='WinSta0', desktop=cfg['desktop'])
        assert sha(__file__) == cfg['worker_sha256']
        os.environ['PATH'] = cfg['git_directory'] + ';' + os.environ['PATH']
        assert subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() == cfg['source_commit']
        built = json.loads((work / 'build.json').read_text())
        assert built['status'] == 'built-current-Windows-attachment-driver' and built['source_commit'] == cfg['source_commit']
        assert sha(work / 'build.json') == cfg['driver_build_sha256']
        data, planets = Path(cfg['data']), Path(cfg['planets'])
        original_data = data_inputs.inspect(data, planets)
        report['data_inputs'] = original_data
        allowed = {(configuration, profile) for configuration in ('Debug', 'Release') for profile in ('automatic', 'sse2')}
        assert cfg['profiles'] and len(cfg['profiles']) == len(set(map(tuple, cfg['profiles'])))
        assert set(map(tuple, cfg['profiles'])) <= allowed and 1 <= cfg['worlds'] <= 20
        cases = json.loads((source / 'Tests/Production/RemainingStock/cases.json').read_text())
        case_list = cases['cases']
        scene = 'Scenarios/Space Shuttle Atlantis/Atlantis ISS Resupply.scn'
        case = next(case for case in case_list if case['scenario_entry_point'] == scene)
        os.environ.update(LIBGL_ALWAYS_SOFTWARE='true', GALLIUM_DRIVER='llvmpipe', LP_NUM_THREADS='2')
        for configuration, math_profile in cfg['profiles']:
            profile = configuration + '-' + math_profile
            runtime = work / ('runtime-' + configuration)
            protected = built['configurations'][configuration]['runtime_files_sha256']
            assert all(sha(runtime / name) == expected for name, expected in protected.items())
            folder = output / profile
            folder.mkdir()
            for path in runtime.iterdir():
                if path.is_file() and path.suffix.lower() in ('.dll', '.exe'):
                    shutil.copy2(path, folder / path.name)
            for name in ('Config', 'Modules', 'Meshes', 'Images', 'Script', 'Textures', 'Textures2'):
                if (runtime / name).is_dir():
                    shutil.copytree(runtime / name, folder / name, copy_function=link_or_copy)
            for body, names in {'Earth':('EarthAtm2006','EarthAtmJ71G','EarthAtmNRLMSISE00'),'Mars':('MarsAtm2006',),'Venus':('VenusAtm2006',)}.items():
                for name in names:
                    target = folder / 'Modules/Celbody' / body / 'Atmosphere' / (name + '.dll')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(folder / 'Modules/Celbody/Atmosphere' / (name + '.dll'), target)
            for name in ('Kernels', 'Textures', 'Textures2', 'GravityModels', 'Fonts'):
                shutil.copytree(data / name, folder / name, dirs_exist_ok=True, copy_function=link_or_copy)
            for name in json.loads((source / 'Tests/Production/standard-planets.lock.json').read_text())['data_files']:
                target = folder / name
                target.parent.mkdir(parents=True, exist_ok=True)
                link_or_copy(planets / name, target)
            target = folder / scene
            target.parent.mkdir(parents=True)
            target.write_bytes((source / scene).read_bytes())
            inputs.stage_delivery_repairs(folder, cases, json.loads((runtime / 'test-runtime.json').read_text())['files'])
            text = (source / 'Tests/Production/Fixtures/Orbiter.cfg').read_text()
            for line in ('PropStages = 1\n','PropStage0 = 1 1 1\n','PropSubsampling = 1\n'):
                assert text.count(line) == 1
                text = text.replace(line, '')
            text = text.replace('  ProductionReferenceDriver', '  ProductionAttachmentTeardownDriver\n  OGLClient')
            assert 'StartPaused = FALSE' in text and 'ShutdownMode = 0' in text
            (folder / 'Orbiter.cfg').write_text(text + '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\n')
            (folder / 'staged-Orbiter.cfg').write_bytes((folder / 'Orbiter.cfg').read_bytes())
            (folder / 'attachment-case.txt').write_text(f"{cfg['worlds']} 60 {math_profile}\nSpace Shuttle Atlantis/Atlantis ISS Resupply.scn\n")
            (folder / 'ogl-evidence.enabled').touch()
            mesa_files(Path(cfg['mesa']), folder)
            bindings = json.loads((folder / 'mesa-bindings.json').read_text())
            expected = {}
            for name, value in protected.items():
                if name.lower().endswith(('.dll', '.exe')):
                    expected.setdefault(Path(name).name.lower(), set()).add(value)
            for name, item in bindings['runtime']['files'].items():
                if name.lower().endswith(('.dll', '.exe')):
                    expected.setdefault(Path(name).name.lower(), set()).add(item['sha256'])
            guards = {path.relative_to(folder).as_posix(): sha(path) for name in ('Config','Meshes','Script','Scenarios')
                      for path in (folder / name).rglob('*') if path.is_file()}
            argv = [str(folder / 'Orbiter.exe'), '--scenario=Space Shuttle Atlantis/Atlantis ISS Resupply', '--fixedstep=0.015625', '--maxframes=60']
            invocation = dict(argv=argv, source_commit=cfg['source_commit'], original_scenario_sha256=sha(source / scene),
                              original_inputs_sha256=guards, worlds=cfg['worlds'], configuration=configuration, math_profile=math_profile,
                              normal_cleanup_required=True, no_physics_steps_required=True, startup_configuration_sha256=sha(folder / 'staged-Orbiter.cfg'))
            (folder / 'invocation.json').write_text(json.dumps(invocation, indent=2) + '\n')
            with (folder / 'console.txt').open('w') as console:
                process = subprocess.Popen(argv, cwd=folder, stdout=console, stderr=subprocess.STDOUT)
                receipt = dict(profile=profile, actual_pid=process.pid, timeout_seconds=1800)
                report['actual_processes'].append(receipt)
                report['status'] = 'running-' + profile
                save()
                try:
                    receipt['actual_returncode'] = process.wait(timeout=1800)
                    receipt['timed_out'] = False
                except subprocess.TimeoutExpired:
                    process.kill()
                    receipt.update(actual_returncode=process.wait(), timed_out=True)
                save()
                assert receipt['actual_returncode'] == 0 and not receipt['timed_out'], 'Actual normal-cleanup application failed'
            assert all(sha(folder / name) == expected for name, expected in guards.items())
            assert data_inputs.inspect(data, planets) == original_data
            report['results'][profile] = inspect(folder, cfg['worlds'], math_profile, expected)
            assert all(sha(runtime / name) == expected for name, expected in protected.items())
            save()
        diagnostic = cfg['worlds'] < 20 or set(map(tuple, cfg['profiles'])) != allowed
        report.update(status='passed-diagnostic-only' if diagnostic else 'passed-current-Windows-paused-lifetime',
                      diagnostic_only=diagnostic,
                      original_inputs_and_current_runtimes_unchanged=True)
    except BaseException as error:
        report.update(status='failed', error=str(error), traceback=traceback.format_exc())
    finally:
        save()
        archive = request.parent / (cfg['name'] + '-observations.zip')
        assert not archive.exists()
        members = {}
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as target:
            for path in output.rglob('*'):
                if path.is_file() and path.suffix.lower() in ('.json','.csv','.txt','.log','.cfg','.scn'):
                    name = path.relative_to(output).as_posix()
                    target.write(path, name)
                    members[name] = sha(path)
        with zipfile.ZipFile(archive) as target:
            assert set(target.namelist()) == set(members) and all(hashlib.sha256(target.read(name)).hexdigest() == value for name,value in members.items())
        (request.parent / (cfg['name'] + '-preservation.json')).write_text(json.dumps(dict(archive_sha256=sha(archive), files_sha256=members), indent=2) + '\n')
    sys.exit(0 if report['status'].startswith('passed') else 1)


if __name__ == '__main__':
    main()
