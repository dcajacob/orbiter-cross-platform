#!/usr/bin/env python3
"""Measure fixed stock scenes on the real desktop; never substitute a virtual display."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def host_state():
    power = {}
    for device in Path('/sys/class/power_supply').glob('*'):
        power[device.name] = {name:(device/name).read_text().strip()
                              for name in ('type', 'online', 'status', 'capacity') if (device/name).exists()}
    return dict(time_ns=time.time_ns(), load_average=os.getloadavg(), power=power)


def statistics_ms(values):
    require(values and all(math.isfinite(v) and v>0 for v in values), 'Invalid frame durations')
    ordered = sorted(values)
    return dict(samples=len(values), median_ms=statistics.median(ordered),
                p95_ms=ordered[math.ceil(.95*len(ordered))-1],
                p99_ms=ordered[math.ceil(.99*len(ordered))-1],
                minimum_ms=ordered[0], maximum_ms=ordered[-1], mean_ms=statistics.mean(ordered))


def audit(out, profile, backend, frames, warmup, samples, case):
    life = json.loads((out/'graphics-lifecycle.json').read_text())
    require(life['context_deleted'] and life['successful_presents']==life['rendered_frames']==frames,
            'Application did not present the complete workload and shut down normally')
    window = json.loads((out/'native-window.json').read_text())
    renderer = json.loads((out/'renderer-info.json').read_text())
    require(window['backend']==backend and window['engineering_scale']==1 and
            window['framebuffer_width']==window['requested_width']==profile['width'] and
            window['framebuffer_height']==window['requested_height']==profile['height'],
            'Actual desktop backend or window/framebuffer geometry differs')
    if backend=='wayland':
        require(abs(window['logical_width']*window['content_scale_x']-profile['width'])<1 and
                abs(window['logical_height']*window['content_scale_y']-profile['height'])<1,
                'Wayland logical dimensions and actual surface scale differ from framebuffer')
    else:
        require(window['logical_width']==profile['width'] and window['logical_height']==profile['height'],
                'X11 client dimensions differ from framebuffer pixels')
    require(renderer['client_width']==profile['width'] and renderer['client_height']==profile['height'] and
            renderer['vendor']=='Intel' and 'llvmpipe' not in renderer['renderer'].lower(),
            'Performance gate requires the real Intel GPU at the declared dimensions')
    settings = json.loads((out/'native-render-settings.json').read_text())
    require(settings==profile['settings'], 'Actual renderer quality differs from fixed medium profile')
    pane = json.loads((out/'cockpit-viewport.json').read_text())
    require(pane==dict(width=profile['width'],height=profile['height']),
            'Original cockpit dimensions differ from actual framebuffer dimensions')
    cockpit = rows(out/'cockpit-state.csv')
    if case['internal']:
        require(len(cockpit)==frames+1 and all(int(r['cockpit'])==case['cockpit'] and
                r['class']==case['class'] and int(r['left_mfd'])==case['left_mfd'] and
                int(r['right_mfd'])==case['right_mfd'] for r in cockpit),
                'Requested stock cockpit did not remain active for every original physics tick')
    else:
        # This trace starts on the first actual internal-camera frame; the
        # original host never enters that observation path for an exterior run.
        require(not cockpit, 'Fixed exterior run entered an internal camera')
    draws = rows(out/'object-draws-all.csv')
    meshes = rows(out/'visual-meshes.csv')
    require(meshes and all(r['class']==case['class'] and int(r['groups'])>0 for r in meshes),
            'Requested stock visual meshes did not load')
    # The existing per-object counter covers scene meshes. Original 2D panels
    # render through clbkRender2DPanel outside that counter; their complete live
    # cockpit/MFD traces above establish the separate panel workload.
    if not case['internal'] or case['cockpit']!=2:
        require(draws and any(int(r['mesh_draw_calls'])>0 for r in draws), 'Scene did not draw actual stock meshes')
    errors = out/'graphics-errors.txt'
    require(not errors.exists() or not errors.read_text().strip(), 'Performance run has OpenGL errors')
    timings = rows(out/'frame-times.csv')
    require(len(timings)==frames and [int(r['frame']) for r in timings]==list(range(1, frames+1)),
            'Incomplete or reordered timing records')
    for r in timings:
        require(int(r['framebuffer_width'])==profile['width'] and int(r['framebuffer_height'])==profile['height'] and
                r['visible']=='1' and r['iconified']=='0', 'Window changed size, was hidden or minimized')
        require(int(r['loop_start_ns'])<=int(r['swap_start_ns'])<=int(r['present_end_ns']),
                'Nonmonotonic frame timing phases')
    # Primary metric includes the previous timing CSV write, application loop
    # bookkeeping, event polling, original physics, GUI, rendering and swapping.
    # No slow frames are trimmed from the predeclared measurement interval.
    selected = timings[warmup:warmup+samples]
    cadence = [(int(timings[i]['present_end_ns'])-int(timings[i-1]['present_end_ns']))/1e6
               for i in range(warmup, warmup+samples)]
    workload = [(int(r['present_end_ns'])-int(r['loop_start_ns']))/1e6 for r in selected]
    swapping = [(int(r['present_end_ns'])-int(r['swap_start_ns']))/1e6 for r in selected]
    require(len(selected)==samples, 'Insufficient measured frames')
    cadence_stats = statistics_ms(cadence)
    return dict(status='passed' if cadence_stats['median_ms']<=profile['median_ms_max'] and
                cadence_stats['p95_ms']<=profile['p95_ms_max'] else 'failed',
                cadence=cadence_stats, poll_to_present=statistics_ms(workload),
                swap=statistics_ms(swapping), window=window, cockpit_viewport=pane, renderer=renderer, settings=settings, lifecycle=life,
                focused_frames=sum(r['focused']=='1' for r in selected),
                elapsed_sample_seconds=sum(cadence)/1000)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('executable', 'assets', 'data', 'modules', 'planets', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--backend', choices=('wayland', 'x11'), required=True)
    p.add_argument('--display', default=os.environ.get('DISPLAY', ':0'))
    p.add_argument('--wayland-display', default='wayland-0')
    p.add_argument('--case', action='append')
    p.add_argument('--smoke', action='store_true', help='80 timing samples; never a performance qualification')
    a = p.parse_args()
    for name in ('executable', 'assets', 'data', 'modules', 'planets', 'output'):
        setattr(a, name, getattr(a, name).resolve())
    profile = json.loads((HERE/'cases.json').read_text())
    cases = [c for c in profile['cases'] if not a.case or c['id'] in a.case]
    require(cases and (not a.case or set(a.case)<={c['id'] for c in cases}), 'Unknown performance case')
    require(a.backend!='x11' or a.display==':0', 'Hardware qualification requires the real desktop XWayland :0')
    require(a.backend!='wayland' or a.wayland_display=='wayland-0', 'Hardware qualification requires the desktop wayland-0')
    for case in cases:
        for source in (ROOT/'Scenarios'/case['scenario'], a.assets/'Scenarios'/case['scenario']):
            require(digest(source)==case['sha256'], 'Unchanged stock scenario differs: '+str(source))
    a.output.mkdir(parents=True, exist_ok=False)
    warmup, samples, repeats = (20, 80, 1) if a.smoke else (profile['warmup_frames'], profile['sample_frames'], profile['repeats'])
    frames = warmup+samples
    env = dict(os.environ, LD_LIBRARY_PATH=str(a.executable.parent), XDG_SESSION_TYPE=a.backend)
    for name in ('LD_PRELOAD', 'LIBGL_ALWAYS_SOFTWARE', 'GALLIUM_DRIVER', 'MESA_LOADER_DRIVER_OVERRIDE', 'LIBGL_DRIVERS_PATH'):
        env.pop(name, None)
    if a.backend=='wayland':
        env.pop('DISPLAY', None)
        env['WAYLAND_DISPLAY'] = a.wayland_display
    else:
        env.pop('WAYLAND_DISPLAY', None)
        env['DISPLAY'] = a.display
    inputs = dict(executable=digest(a.executable), renderer=digest(a.modules/'Graphics/OGLClient.so'),
                  engine=digest(a.executable.parent/'liborbiter_production_vessels.so'))
    sources = [Path(__file__), HERE/'cases.json', HERE/'medium.cfg', ROOT/'OVP/OGLClient/Native/LinuxAdapter.cpp',
               ROOT/'Src/Orbiter/Production/NativeApplication.cpp']
    report = dict(status='pending', phase6_complete=False, smoke=a.smoke, backend=a.backend,
                  platform=platform.platform(), profile_sha256=digest(HERE/'cases.json'), inputs_sha256=inputs,
                  source_sha256={str(path.relative_to(ROOT)):digest(path) for path in sources},
                  method='Consecutive present-end steady-clock timestamps; bounded original fixed-step workload, one physics tick per rendered frame',
                  warmup_frames=warmup, sample_frames=samples, repeats=repeats,
                  environment={name:env[name] for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'XDG_RUNTIME_DIR', 'XDG_SESSION_TYPE', 'LD_LIBRARY_PATH') if name in env},
                  cases={}, host_before=host_state())
    try:
        for case in cases:
            for repeat in range(1, repeats+1):
                name=case['id']+'-'+str(repeat)
                out=a.output/name
                out.mkdir()
                (out/'Orbiter.cfg').write_bytes((HERE/'medium.cfg').read_bytes())
                (out/'frame-times.enabled').write_text('Full frame timing; fixed benchmark interval\n')
                argv = [str(a.executable)]
                for key in ('assets', 'data', 'modules', 'planets'):
                    argv += ['--'+key, str(getattr(a, key))]
                argv += ['--config', str(out/'Orbiter.cfg'), '--scenario', str(a.assets/'Scenarios'/case['scenario']),
                         '--evidence', str(out), '--frames', str(frames), '--fixed-step', repr(profile['fixed_step']), '--run']
                (out/'invocation.json').write_text(json.dumps(argv, indent=2)+'\n')
                before = host_state()
                with (out/'console.log').open('w') as log:
                    process = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
                    try:
                        deadline = time.monotonic()+30
                        while not (out/'renderer-info.json').exists() and process.poll() is None and time.monotonic()<deadline:
                            time.sleep(.05)
                        require(process.poll() is None, 'Desktop application exited during initialization: '+name)
                        require((out/'renderer-info.json').exists(), 'Desktop renderer did not initialize: '+name)
                        (out/'loaded-maps.txt').write_text(Path(f'/proc/{process.pid}/maps').read_text())
                        require(process.wait(timeout=240)==0, 'Desktop performance application failed: '+name)
                    finally:
                        if process.poll() is None:
                            process.terminate()
                            try:process.wait(timeout=10)
                            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
                result=audit(out, profile, a.backend, frames, warmup, samples, case)
                result.update(scenario=case['scenario'], scenario_sha256=case['sha256'], host_before=before, host_after=host_state())
                result['files_sha256']={file:digest(out/file) for file in ('frame-times.csv', 'native-window.json',
                    'native-render-settings.json', 'renderer-info.json', 'graphics-lifecycle.json', 'loaded-maps.txt',
                    'cockpit-state.csv', 'cockpit-viewport.json', 'flight-state.csv', 'object-draws-all.csv', 'visual-meshes.csv')}
                report['cases'][name]=result
                (out/'performance.json').write_text(json.dumps(result, indent=2)+'\n')
                print(json.dumps(dict(backend=a.backend, case=name, smoke=a.smoke, status=result['status'], cadence=result['cadence'])), flush=True)
        require(digest(a.executable)==inputs['executable'] and digest(a.modules/'Graphics/OGLClient.so')==inputs['renderer'] and
                digest(a.executable.parent/'liborbiter_production_vessels.so')==inputs['engine'], 'Application binaries changed during measurement')
        require(all(digest(ROOT/path)==checksum for path,checksum in report['source_sha256'].items()), 'Benchmark sources changed during measurement')
        require(all(r['status']=='passed' for r in report['cases'].values()), 'Hardware frame-time budget failed')
        report['status']='smoke-only' if a.smoke else 'passed'
    except BaseException as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        report['host_after']=host_state()
        (a.output/'performance-report.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__=='__main__':
    main()
