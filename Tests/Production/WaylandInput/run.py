#!/usr/bin/env python3
"""Drive original Orbiter controls through a private Weston seat and actual GLFW."""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE), str(HERE.parent/'Cockpit'), str(HERE.parent/'Flight'),
                str(HERE.parent/'DeltaGlider'), str(HERE.parent/'CockpitControls'), str(HERE.parent)]
from compositor import Compositor
from keyboard_smoke import require, wait
from reference import fixture
from systems import digest
from window_keys import input_state
from window_panel import rows
from window_camera import verify, arm_shutdown, verify_shutdown
from frozen_controls import metadata

KEYS = dict(Escape=1, w=17, Control_L=29, Shift_L=42, Alt_L=56, space=57,
            Home=102, F1=59, F6=64, x=45, z=44)


class Transport:
    def __init__(self, compositor, pid, sink, output, ratio):
        self.compositor, self.pid, self.sink = compositor, pid, sink
        self.output, self.ratio = output, ratio
        self.held_buttons = set()

    def cursor(self):
        r = self.compositor.surface(self.pid)
        return tuple(int(round(r[name]*self.ratio)) for name in ('cursor_x', 'cursor_y'))

    def gui_point(self, point):
        # ImGui uses logical window units; cockpit picks use framebuffer pixels.
        return tuple(int(round(v*self.ratio)) for v in point)

    def dialog_adjustment(self, dialog):
        x, y, width = (float(dialog[k]) for k in ('x', 'y', 'width'))
        logical_width = self.compositor.surface(self.pid)['width']
        if x+width>logical_width:
            return self.gui_point((x+100, y+11)), self.gui_point((max(10, logical_width-width+92), y+11))
        return None

    def focused(self):
        return self.compositor.command('state')['keyboard_pid']

    def transfer(self, pid):
        self.compositor.command('focus '+str(pid))
        wait(lambda: self.focused()==pid, 'Compositor did not transfer actual keyboard focus')
        releases = []
        if pid != self.pid and self.held_buttons:
            wait(lambda: rows(self.output/'cockpit-camera.csv')[-1]['mouse_rotation']=='0',
                 'Camera did not release on real Wayland focus loss')
            # Release physical buttons while focus is away, before reentering.
            # GLFW has already synthesized its application-side release.
            for number in list(self.held_buttons):
                releases.append(('left_up' if number==1 else 'right_up', *self.cursor()))
                self.emit(number, False)
        return releases

    def key(self, pid, name, down):
        self.compositor.command(f'key {pid} {KEYS[name]} {int(down)}')

    def move(self, point):
        x, y = (v/self.ratio for v in point)
        self.compositor.command(f'move {self.pid} {x:.12g} {y:.12g}')
        time.sleep(.06)

    def motion(self, dx, dy):
        self.compositor.command(f'motion {dx/self.ratio:.12g} {dy/self.ratio:.12g}')

    def emit(self, number, down, point=None):
        if point is not None:
            self.move(point)
        if number in (4, 5):
            if down:
                self.compositor.command(f'wheel {self.pid} {1 if number==4 else -1}')
        else:
            self.compositor.command(f'button {self.pid} {272 if number==1 else 273} {int(down)}')
            if down:
                self.held_buttons.add(number)
            else:
                self.held_buttons.discard(number)

    def button(self, pid, x, y, down, number=1):
        require(pid == self.pid, 'Pointer target differs from owned Orbiter')
        self.emit(number, down, (x, y))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('dependencies', 'executable', 'assets', 'data', 'modules', 'planets', 'frozen', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    cases = json.loads((HERE.parent/'CockpitControls/cases.json').read_text())['cases']
    p.add_argument('--case', choices=[c['id'] for c in cases if c['cockpit']!=1], default='controls_dg_panel')
    p.add_argument('--configuration', choices=('Debug', 'Release'), default='Release')
    p.add_argument('--scale', type=int, choices=(1, 2), default=1)
    p.add_argument('--renderer', choices=('llvmpipe', 'default'), default='llvmpipe')
    p.add_argument('--camera-check', choices=('all', 'drag', 'wheel', 'step'), default='all')
    a = p.parse_args()
    tools_manifest = json.loads((a.dependencies/'test-tools.json').read_text())
    require(tools_manifest['status']=='passed' and
            tools_manifest['lock_sha256']==digest(HERE/'dependencies.lock.json'), 'Private dependency lock differs')
    for name, checksum in tools_manifest['source_sha256'].items():
        require(digest(HERE/name)==checksum, 'Private test tool source changed: '+name)
    for name, checksum in tools_manifest['outputs_sha256'].items():
        require(digest(a.dependencies/name)==checksum, 'Private test tool binary changed: '+name)
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    case = next(c for c in cases if c['id']==a.case)
    pins = metadata()
    require(json.loads((a.frozen/'provenance.json').read_text())==pins, 'Frozen Windows controls differ')
    relative = Path(a.configuration)/(case['id']+'-1')/'control-inputs.csv'
    frozen = a.frozen/relative
    require(digest(frozen)==pins['reference_files_sha256'][a.configuration][relative.relative_to(a.configuration).as_posix()],
            'Frozen Windows click coordinates differ')
    points = [(int(r['x']), int(r['y'])) for r in rows(frozen) if r['event']=='left_down']
    require(len(points)==2, 'Original RCS mode click schedule differs')
    (out/'cockpit.scn').write_text(fixture(case).replace('BEGIN_SHIPS',
        'BEGIN_MFD Left\n  TYPE Orbit\n  REF Earth\nEND_MFD\nBEGIN_MFD Right\n  TYPE Surface\nEND_MFD\nBEGIN_SHIPS'))
    (out/'Orbiter.cfg').write_text((ROOT/'Tests/Production/NativeScene/Orbiter.cfg').read_text()+
        '\nFPS = 0\nMenubarMode = 1\nInfobarMode = 1\nInstrumentUpdateInterval = 0.25\n')
    for name in ('control-evidence', 'vc-picking', 'camera-pointer', 'ui-evidence', 'menu-evidence'):
        (out/(name+'.enabled')).write_text('Actual private Wayland input acceptance\n')
    if case['cockpit']==2:
        (out/'panel-picking.enabled').write_text('Read-only original panel geometry\n')
    if a.scale==2:
        (out/'window-scale.enabled').write_text('2\n')
    argv = [str(a.executable.resolve())]
    for name in ('assets', 'data', 'modules', 'planets'):
        argv += ['--'+name, str(getattr(a, name).resolve())]
    argv += ['--config', str(out/'Orbiter.cfg'), '--scenario', str(out/'cockpit.scn'),
             '--evidence', str(out), '--keymap', str(ROOT/'Tests/Production/Flight/keymap-dg-laptop.cfg'), '--run']
    (out/'invocation.json').write_text(json.dumps(argv, indent=2)+'\n')
    report = dict(status='failed', case=case['id'], scale=a.scale, phase6_complete=False)
    inputs_sha256 = dict(executable=digest(a.executable), renderer=digest(a.modules/'Graphics/OGLClient.so'))
    try:
        with Compositor(a.dependencies, out/'compositor', a.scale,
                        'pixman' if a.renderer=='llvmpipe' else 'gl') as compositor:
            environment = dict(compositor.environment, LP_NUM_THREADS='2',
                               LD_LIBRARY_PATH=str(a.executable.resolve().parent))
            if a.renderer=='llvmpipe':
                environment.update(LIBGL_ALWAYS_SOFTWARE='1', GALLIUM_DRIVER='llvmpipe')
            else:
                for name in ('LIBGL_ALWAYS_SOFTWARE', 'GALLIUM_DRIVER'):
                    environment.pop(name, None)
            with (out/'focus-sink.log').open('w') as sink_log, (out/'console.log').open('w') as log:
                sink = subprocess.Popen([str(a.dependencies.resolve()/'focus-sink')], env=environment,
                                        stdout=sink_log, stderr=subprocess.STDOUT)
                process = None
                try:
                    wait(lambda: compositor.surface(sink.pid), 'Owned focus sink did not map')
                    process = subprocess.Popen(argv, env=environment, stdout=log, stderr=subprocess.STDOUT)
                    surface = wait(lambda: compositor.surface(process.pid), 'Owned Wayland Orbiter did not map')
                    wait(lambda: (out/'cockpit-camera.csv').exists() and rows(out/'cockpit-camera.csv') and
                         input_state(out) and input_state(out)[0]>=2, 'Requested cockpit did not initialize')
                    def geometry_ready():
                        geometry = json.loads((out/'native-window.json').read_text())
                        return geometry if geometry['framebuffer_width']==1280 and geometry['framebuffer_height']==720 else None
                    geometry = wait(geometry_ready, 'Actual Wayland framebuffer did not reach 1280x720')
                    require(geometry['backend']=='wayland', 'Actual renderer is not native Wayland')
                    require(geometry['logical_width']==1280//a.scale and geometry['logical_height']==720//a.scale and
                            geometry['framebuffer_width']==1280 and geometry['framebuffer_height']==720 and
                            geometry['engineering_scale']==a.scale,
                            'Actual GLFW logical/framebuffer geometry does not prove requested scaling')
                    compositor.command('views '+str(process.pid))
                    require(surface['width']==1280//a.scale and surface['height']==720//a.scale,
                            'Compositor logical size does not prove requested scaling')
                    t = Transport(compositor, process.pid, sink.pid, out, a.scale)
                    t.transfer(process.pid)
                    def delivered(name, down, pid=None):
                        before = input_state(out)[0]
                        t.key(pid or process.pid, name, down)
                        if pid is None:
                            wait(lambda: (s:=input_state(out)) and s[0]>before and bool(s[1][KEYS[name]])==down,
                                 'Actual Wayland key state differs: '+name)
                    def thrust(value):
                        tick = input_state(out)[0]
                        def sample():
                            complete = rows(out/'thrust-state.csv')
                            return next((r for r in reversed(complete) if int(r['input_tick'])>=tick and
                                         float(r['rcs'])==value), None)
                        return wait(sample,
                                    'Actual RCS thrust differs: '+str(value))
                    delivered('w', True)
                    start = input_state(out)[0]
                    wait(lambda: input_state(out)[0]>=start+3, 'No finalized bare-W samples')
                    thrust(0)
                    delivered('w', False)
                    full = []
                    for point, mode in zip(points, (2, 1)):
                        for down in (True, False):
                            before = len(rows(out/'control-inputs.csv'))
                            t.button(process.pid, *point, down)
                            wait(lambda: len(rows(out/'control-inputs.csv'))>before, 'Actual RCS pick was not delivered')
                        wait(lambda: int(rows(out/'cockpit-state.csv')[-1]['rcs_mode'])==mode,
                             'Original RCS mouse pick missed through Wayland')
                        delivered('Alt_L', True)
                        delivered('w', True)
                        full.append(thrust(1))
                        delivered('w', False)
                        delivered('Alt_L', False)
                        thrust(0)
                    delivered('Shift_L', True)
                    delivered('Alt_L', True)
                    delivered('w', True)
                    precision = thrust(.1)
                    delivered('w', False)
                    delivered('Alt_L', False)
                    delivered('Shift_L', False)
                    thrust(0)
                    delivered('Alt_L', True)
                    delivered('w', True)
                    held = thrust(1)
                    t.transfer(sink.pid)
                    released = thrust(0)
                    wait(lambda: not input_state(out)[1][17], 'Focus loss did not clear actual held W')
                    delivered('w', False, sink.pid)
                    delivered('Alt_L', False, sink.pid)
                    t.transfer(process.pid)
                    thrust(0)
                    camera = verify(out, process.pid, sink.pid, t.key, t.button, None, None, None,
                                    t.focused, t.transfer, points[0], case['cockpit'], a.camera_check, transport=t)
                    shutdown = arm_shutdown(out, process.pid, t.button)
                    (out/'loaded-maps.txt').write_text(Path(f'/proc/{process.pid}/maps').read_text())
                    t.key(process.pid, 'Escape', True)
                    require(process.wait(timeout=20)==0, 'Actual Wayland Orbiter session failed')
                    camera['shutdown'] = verify_shutdown(out, shutdown)
                    lifecycle = json.loads((out/'graphics-lifecycle.json').read_text())
                    require(lifecycle['context_deleted'] and lifecycle['successful_presents']>0,
                            'Wayland session did not present and shut down normally')
                    errors = out/'graphics-errors.txt'
                    require(not errors.exists() or not errors.read_text().strip(), 'Wayland session OpenGL errors')
                    actual = [(r['event'], int(r['x']), int(r['y'])) for r in rows(out/'control-inputs.csv')]
                    expected = [(kind, *point) for point in points for kind in ('left_down', 'left_up')]
                    expected += [tuple(e) for e in camera['events']]+[tuple(shutdown['event'])]
                    require(actual==expected, 'Wayland mouse event order or framebuffer coordinates differ')
                    require(digest(a.executable)==inputs_sha256['executable'] and
                            digest(a.modules/'Graphics/OGLClient.so')==inputs_sha256['renderer'],
                            'Application binaries changed during input session')
                    renderer = json.loads((out/'renderer-info.json').read_text())
                    require(('llvmpipe' in renderer['renderer'].lower()) == (a.renderer=='llvmpipe'),
                            'Actual OpenGL renderer differs from requested driver')
                    report.update(status='passed', actual_backend='wayland', geometry=geometry, surface=surface,
                        renderer=renderer, test_tools_sha256=digest(a.dependencies/'test-tools.json'),
                        reference=dict(run=pins['run_id'], file=relative.as_posix(), sha256=digest(frozen)),
                        actual_rcs_picks=True, bare_w_neutral=True, full_thrust=full, precision=precision,
                        keyboard_focus_loss=dict(held=held, released=released), camera=camera, lifecycle=lifecycle,
                        transport='Private Weston seat -> Wayland protocols -> actual GLFW callbacks -> original Orbiter',
                        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in
                            [Path(__file__), HERE/'compositor.py', HERE/'CompositorInput.c', HERE/'FocusSink.c',
                             HERE.parent/'DeltaGlider/window_camera.py']},
                        executable_sha256=digest(a.executable),
                        renderer_sha256=digest(a.modules/'Graphics/OGLClient.so'),
                        test_module_sha256=digest(a.dependencies/'compositor-input.so'))
                finally:
                    if process and process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            process.kill();process.wait(timeout=10)
                    sink.terminate();sink.wait(timeout=10)
    except BaseException as error:
        report['error'] = str(error)
        raise
    finally:
        (out/'wayland-input.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(status=report['status'], case=a.case, scale=a.scale,
                          presents=report['lifecycle']['successful_presents'])))


if __name__=='__main__':
    main()
