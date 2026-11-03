"""Exercise camera pointer capture, wheel routing and stepped FOV via real X11 input."""
import ctypes as C
import json
import math
from pathlib import Path

from keyboard_smoke import require, wait
from systems import digest
from window_keys import input_state
from window_panel import rows

SOURCE_SHA256 = digest(Path(__file__))
NORMAL_CURSOR = 0x34001


def verify(out, window, destination, key, button, send, x, display, focused, transfer,
           rcs_point, cockpit, selection='all'):
    out = Path(out)
    (out/'camera-driver.py').write_bytes(Path(__file__).read_bytes())
    x.XQueryPointer.argtypes = [C.c_void_p, C.c_ulong, C.POINTER(C.c_ulong), C.POINTER(C.c_ulong),
                               *([C.POINTER(C.c_int)]*4), C.POINTER(C.c_uint)]
    events, stages = [], []
    anchor = None
    codes = dict(space=57, Home=0xc7, F1=59, F6=64, Control_L=29, x=45, z=44)

    def camera():
        return rows(out/'cockpit-camera.csv')[-1]

    def advance(ticks=5):
        before = input_state(out)[0]
        wait(lambda: input_state(out)[0] >= before+ticks, 'No camera input/release samples')

    def deliver(name, down):
        before = input_state(out)[0]
        key(window, name, down)
        wait(lambda: (state := input_state(out)) and state[0] > before and
             bool(state[1][codes[name]]) == down, 'Camera key did not reach actual input: '+name)

    def tap(name):
        deliver(name, True)
        deliver(name, False)

    def cursor():
        root, child = C.c_ulong(), C.c_ulong()
        rx, ry, wx, wy, mask = C.c_int(), C.c_int(), C.c_int(), C.c_int(), C.c_uint()
        require(x.XQueryPointer(display, window, C.byref(root), C.byref(child), C.byref(rx), C.byref(ry),
                                C.byref(wx), C.byref(wy), C.byref(mask)), 'Cannot query actual owned-window pointer')
        return wx.value, wy.value

    def emit(number, down, point=None):
        before = len(rows(out/'control-inputs.csv'))
        if point is not None:
            button(window, *point, down, number)
        else:
            physical = cursor()
            send(window, 4 if down else 5, number, 0 if down else 1 << (7+number), *physical)
        if number in (4, 5):
            if not down:
                return
            kind = 'wheel'
        else:
            kind = ('left_' if number == 1 else 'right_')+('down' if down else 'up')
        expected = point if point is not None else anchor or cursor()
        events.append((kind, *expected))
        wait(lambda: len(rows(out/'control-inputs.csv')) > before, 'Camera mouse event did not reach the window: '+kind)
        (out/'camera-actions.json').write_text(json.dumps(dict(events=events, stages=stages), indent=2)+'\n')

    def motion(dx, dy):
        require(camera()['mouse_rotation'] == '1' and focused() == window,
                'Relative pointer fixture requires the owned focused camera grab')
        # GLFW recenters the server pointer and derives relative movement from
        # MotionNotify. XWayland ignores synthetic server warps while grabbed;
        # deliver that X11 event directly to this harness's owned window.
        px, py = cursor()
        send(window, 6, 0, 0, px+dx, py+dy)
        x.XSync(display, False)

    def acquire(point):
        before = camera()
        emit(3, True, point)
        wait(lambda: camera()['mouse_rotation'] == '1', 'Camera did not acquire the pointer')
        # The event trace is written before GLFW enters disabled cursor mode.
        # Wait for completed input samples before moving its recentered pointer.
        advance(3)
        require(all(camera()[k] == before[k] for k in ('phi', 'theta')),
                'Entering camera capture introduced a synthetic view jump')

    def recenter():
        tap('Home')
        wait(lambda: abs(float(camera()['phi'])) < 1e-10 and abs(float(camera()['theta'])) < 1e-10,
             'Original Home did not recenter the mouse-controlled view')

    def wheel(up, point=(640, 360)):
        number = 4 if up else 5
        emit(number, True, point)
        emit(number, False, point)

    def move(point):
        x.XWarpPointer(display, 0, window, 0, 0, 0, 0, *point)
        x.XSync(display, False)
        advance()

    def options():
        windows = rows(out/'menu-windows.csv')
        return next((r for r in reversed(windows) if r['frame'] == windows[-1]['frame'] and
                     'Orbiter: Options' in r['name']), None)

    start = camera()
    tap('space')
    advance()
    paused_seconds = rows(out/'cockpit-state.csv')[-1]['seconds']
    if selection in ('all', 'drag'):
        anchor = tuple(rcs_point)
        before = camera()
        acquire(anchor)
        motion(100, 60)
        moved = wait(lambda: (r := camera()) and abs(float(r['phi'])-float(before['phi'])) > .1 and
                     abs(float(r['theta'])-float(before['theta'])) > .05 and r,
                     'Right drag did not rotate the cockpit camera', timeout=5)
        require(abs(float(moved['phi'])-float(before['phi'])+.2) < 1e-8 and
                abs(float(moved['theta'])-float(before['theta'])+.12) < 1e-8,
                'Cockpit mouse pixel scale or direction differs from the original')
        recenter()
        # The anchor is an accepted real RCS-LIN pick. While rotation owns the
        # pointer, the original camera handler must consume the left button.
        emit(1, True)
        emit(1, False)
        require(int(rows(out/'cockpit-state.csv')[-1]['rcs_mode']) == 1,
                'A cockpit control consumed a click during camera rotation')
        emit(3, False)
        anchor = None
        advance()
        require(camera().get('mouse_rotation') == '0', 'Pointer capture did not release')
        recenter()
        anchor = tuple(rcs_point)
        acquire(anchor)
        motion(100, 0)
        wait(lambda: abs(float(camera()['phi'])) > .1, 'Camera focus-loss setup did not rotate')
        transfer(destination)
        wait(lambda: focused() == destination and camera().get('mouse_rotation') == '0',
             'Focus loss did not release camera pointer capture')
        events.append(('right_up', *anchor))  # GLFW's verified synthetic release.
        advance()
        stopped = camera()
        advance()
        require(camera()['phi'] == stopped['phi'], 'Camera continued rotating after focus loss')
        transfer(window)
        wait(lambda: focused() == window, 'Camera window did not regain focus')
        advance()
        require(camera()['phi'] == stopped['phi'], 'Camera drag resumed on focus regain')
        anchor = None
        recenter()
        stages.append(dict(check='drag', before=before, moved=moved, focus_released=stopped,
                           original_pixel_scale=True, camera_priority=True, focus_release=True))
        tap('F1')
        wait(lambda: camera()['internal'] == '0', 'Camera mouse fixture did not select external view')
        anchor = (640, 360)
        before = camera()
        acquire(anchor)
        motion(100, 60)
        moved = wait(lambda: (r := camera()) and abs(float(r['phi'])-float(before['phi'])) > .1 and r,
                     'Right drag did not rotate the external camera')
        require(abs(float(moved['phi'])-float(before['phi'])+.25) < 1e-8 and
                abs(float(moved['theta'])-float(before['theta'])+.15) < 1e-8,
                'External mouse pixel scale or direction differs from the original')
        emit(3, False)
        anchor = None
        tap('F1')
        wait(lambda: camera()['internal'] == '1', 'Camera mouse fixture did not return to the cockpit')
        recenter()
        stages.append(dict(check='external_drag', before=before, moved=moved, original_pixel_scale=True))
    if selection in ('all', 'wheel'):
        before = camera()
        wheel(True)
        changed = wait(lambda: (r := camera()) and abs(float(r['aperture'])-float(before['aperture'])) > .01 and r,
                       'Mouse wheel did not change cockpit FOV', timeout=5)
        require(abs(float(changed['aperture'])-float(before['aperture'])+2*math.pi/180) < 1e-12,
                'Original two-degree mouse-wheel FOV change differs')
        wheel(False)
        wait(lambda: abs(float(camera()['aperture'])-float(before['aperture'])) < 1e-12,
             'Reverse wheel did not restore cockpit aperture')
        deliver('Control_L', True)
        wheel(True)
        advance()
        require(abs(float(camera()['aperture'])-float(before['aperture'])) < 1e-12,
                'Ctrl+wheel also changed camera FOV')
        if cockpit == 2:
            # At the native 1280px width, stock DG defscale and extscale
            # are both 1. Original panel zoom must remain at that bound.
            advance()
            require(float(rows(out/'panel-layout.csv')[-1]['scale']) == 1,
                    'Ctrl+wheel exceeded the original panel scale bound')
            wheel(False)
            wait(lambda: float(rows(out/'panel-layout.csv')[-1]['scale']) == 1,
                 'Original reverse panel zoom did not restore its scale')
        deliver('Control_L', False)
        stages.append(dict(check='wheel', before=before, changed=changed, original_fov_step=True,
                           control_modifier_preserved=True, panel_scale_bounded_at_1280=cockpit == 2))
        tap('F1')
        wait(lambda: camera()['internal'] == '0', 'Wheel fixture did not select external view')
        before = camera()
        wheel(True)
        wait(lambda: float(camera()['distance']) < float(before['distance']), 'External wheel did not approach the vessel')
        wheel(False)
        wait(lambda: float(camera()['distance']) > float(before['distance'])*.99, 'External reverse wheel did not retreat')
        tap('F1')
        wait(lambda: camera()['internal'] == '1', 'Wheel fixture did not restore cockpit mode')
    if selection in ('all', 'step'):
        samples = []
        for name, degrees in [('x', 30), ('x', 35), ('z', 30), ('z', 25)]:
            deliver('Control_L', True)
            deliver(name, True)
            changed = wait(lambda: (r := camera()) and abs(float(r['aperture'])-math.radians(degrees)) < 1e-12 and r,
                           'Ctrl+'+name+' did not select the original five-degree FOV step', timeout=5)
            advance(10)
            require(abs(float(camera()['aperture'])-math.radians(degrees)) < 1e-12,
                    'Held stepped-FOV key repeated or matched continuous FOV')
            deliver(name, False)
            deliver('Control_L', False)
            samples.append(changed)
        stages.append(dict(check='step', samples=samples, original_five_degree_steps=True, held_key_does_not_repeat=True))
    if selection == 'all':
        # Exercise real ImGui ownership before the camera fallback. Use the
        # dialog title so the wheel cannot change any option slider.
        # The original menu handler resets its consumed key in the snapshot.
        key(window, 'F6', True)
        advance()
        key(window, 'F6', False)
        advance()
        dialog = wait(options, 'F6 did not open the original Options dialog')
        ox, oy = int(float(dialog['x'])), int(float(dialog['y']))
        point = (ox+100, oy+11)
        move(point)
        wait(lambda: rows(out/'ui-state.csv')[-1]['capture_mouse'] == '1',
             'Options did not capture the real window pointer')
        before = camera()
        transitions = len(rows(out/'camera-capture.csv'))
        wheel(True, point)
        emit(3, True, point)
        move((point[0]+30, point[1]+20))
        emit(3, False, (point[0]+30, point[1]+20))
        advance()
        after = camera()
        require(all(after[k] == before[k] for k in ('phi', 'theta', 'aperture')) and
                after['mouse_rotation'] == '0' and len(rows(out/'camera-capture.csv')) == transitions,
                'Camera consumed pointer input captured by the Options dialog')
        # Right-button movement does not move an ImGui titlebar.
        close = (ox+int(float(dialog['width']))-12, oy+11)
        emit(1, True, close)
        emit(1, False, close)
        wait(lambda: not options(), 'Options close button did not dismiss the dialog')
        move((1270, 300))
        wait(lambda: rows(out/'ui-state.csv')[-1]['capture_mouse'] == '0',
             'Options retained pointer capture after closing')
        stages.append(dict(check='gui_capture', before=before, after=after,
                           actual_options_dialog=True, camera_input_blocked=True))
    require(rows(out/'cockpit-state.csv')[-1]['seconds'] == paused_seconds,
            'Camera mouse/FOV input advanced paused simulation time')
    tap('space')
    report = dict(status='passed', source_sha256=SOURCE_SHA256, selection=selection,
                  original_paused_camera_input=True, events=events, stages=stages, initial_camera=start)
    (out/'camera-mouse.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def arm_shutdown(out, window, button):
    """Leave actual camera capture held so normal session teardown must release it."""
    out = Path(out)
    point = (640, 360)
    button(window, *point, True, 3)
    wait(lambda: rows(out/'cockpit-camera.csv')[-1]['mouse_rotation'] == '1',
         'Shutdown fixture did not acquire real camera capture')
    captured = rows(out/'camera-capture.csv')[-1]
    require(captured['capture'] == '1' and int(captured['cursor_mode']) == 0x34003,
            'Shutdown fixture did not disable the actual GLFW cursor')
    return dict(event=('right_down', *point), captured=captured)


def verify_shutdown(out, setup):
    transitions = rows(Path(out)/'camera-capture.csv')
    require(transitions[-1]['capture'] == '0' and int(transitions[-1]['cursor_mode']) == NORMAL_CURSOR,
            'Normal shutdown did not release the held camera pointer')
    last_capture = max(i for i, row in enumerate(transitions) if row['capture'] == '1')
    require(last_capture < len(transitions)-1, 'No camera release followed the held shutdown capture')
    report = dict(status='passed', setup=setup, transitions=transitions,
                  held_button_shutdown_release=True)
    (Path(out)/'camera-shutdown.json').write_text(json.dumps(report, indent=2)+'\n')
    return report
