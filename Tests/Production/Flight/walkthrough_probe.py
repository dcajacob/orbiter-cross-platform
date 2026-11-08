#!/usr/bin/env python3
"""Inspect and optionally exercise only the staged walkthrough's own X11 window."""
import argparse
import csv
import ctypes as C
import ctypes.util
import importlib.util
import json
from pathlib import Path
import re
import sys
import time
import statistics

ROOT = Path(__file__).resolve().parents[3]

sys.path[:0] = [str(ROOT / 'Tests/Production/Flight'),
               str(ROOT / 'Tests/Production/CockpitUI'),
               str(ROOT / 'Tests/Production/StockScenarios')]
from keyboard_smoke import Event, KeyEvent, require, wait
from window_capture import capture
inventory_spec = importlib.util.spec_from_file_location('walkthrough_stock_inventory', ROOT / 'Tests/Production/StockScenarios/inventory.py')
inventory = importlib.util.module_from_spec(inventory_spec)
inventory_spec.loader.exec_module(inventory)
ships = inventory.ships


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True, help='Staged walkthrough with its own latest-session.json')
    parser.add_argument('--exercise', action='store_true')
    parser.add_argument('--close', action='store_true')
    parser.add_argument('--resize', action='store_true')
    args = parser.parse_args()
    require(sum((args.exercise, args.close, args.resize)) <= 1, 'Select one window-check action')
    HERE = args.candidate.resolve()
    record = json.loads((HERE / 'latest-session.json').read_text())
    pid = record['pid']
    session = Path(record['session'])
    require(session.is_relative_to(HERE / 'sessions'), 'Session is outside the selected candidate')
    require(Path(f'/proc/{pid}/exe').resolve() == Path(record['argv'][0]).resolve(),
            'Recorded process is not the staged walkthrough executable')
    x = C.CDLL(ctypes.util.find_library('X11'))
    x.XOpenDisplay.argtypes = [C.c_char_p]
    x.XOpenDisplay.restype = C.c_void_p
    display = x.XOpenDisplay(None)
    require(display, 'Desktop X11 display is unavailable')
    x.XDefaultRootWindow.argtypes = [C.c_void_p]
    x.XDefaultRootWindow.restype = C.c_ulong
    root = x.XDefaultRootWindow(display)
    x.XInternAtom.argtypes = [C.c_void_p, C.c_char_p, C.c_int]
    x.XInternAtom.restype = C.c_ulong
    atom = x.XInternAtom(display, b'_NET_WM_PID', False)
    x.XQueryTree.argtypes = [C.c_void_p, C.c_ulong, C.POINTER(C.c_ulong), C.POINTER(C.c_ulong), C.POINTER(C.POINTER(C.c_ulong)), C.POINTER(C.c_uint)]
    x.XGetWindowProperty.argtypes = [C.c_void_p, C.c_ulong, C.c_ulong, C.c_long, C.c_long, C.c_int, C.c_ulong, C.POINTER(C.c_ulong), C.POINTER(C.c_int), C.POINTER(C.c_ulong), C.POINTER(C.c_ulong), C.POINTER(C.POINTER(C.c_ubyte))]
    x.XFetchName.argtypes = [C.c_void_p, C.c_ulong, C.POINTER(C.c_void_p)]
    x.XFree.argtypes = [C.c_void_p]
    x.XSetInputFocus.argtypes = [C.c_void_p, C.c_ulong, C.c_int, C.c_ulong]
    x.XRaiseWindow.argtypes = [C.c_void_p, C.c_ulong]
    x.XFlush.argtypes = [C.c_void_p]
    x.XSync.argtypes = [C.c_void_p, C.c_int]
    x.XCloseDisplay.argtypes = [C.c_void_p]
    x.XStringToKeysym.argtypes = [C.c_char_p]
    x.XStringToKeysym.restype = C.c_ulong
    x.XKeysymToKeycode.argtypes = [C.c_void_p, C.c_ulong]
    x.XKeysymToKeycode.restype = C.c_uint
    x.XSendEvent.argtypes = [C.c_void_p, C.c_ulong, C.c_int, C.c_long, C.POINTER(Event)]
    errors = []
    class XError(C.Structure):
        _fields_ = [('type', C.c_int), ('display', C.c_void_p), ('resourceid', C.c_ulong),
                    ('serial', C.c_ulong), ('error_code', C.c_ubyte), ('request_code', C.c_ubyte), ('minor_code', C.c_ubyte)]
    callback = C.CFUNCTYPE(C.c_int, C.c_void_p, C.POINTER(XError))
    @callback
    def on_error(_, event):
        if event.contents.error_code != 3:
            errors.append(int(event.contents.error_code))
        return 0
    x.XSetErrorHandler.argtypes = [callback]
    x.XSetErrorHandler(on_error)

    def title(window):
        value = C.c_void_p()
        if not x.XFetchName(display, window, C.byref(value)) or not value:
            return ''
        result = C.string_at(value).decode(errors='replace')
        x.XFree(value)
        return result

    def owned():
        pending = [root]
        while pending:
            window = pending.pop()
            r, parent, count = C.c_ulong(), C.c_ulong(), C.c_uint()
            children = C.POINTER(C.c_ulong)()
            if x.XQueryTree(display, window, C.byref(r), C.byref(parent), C.byref(children), C.byref(count)):
                pending.extend(children[i] for i in range(count.value))
                if children:
                    x.XFree(children)
            actual, form, items, remaining = C.c_ulong(), C.c_int(), C.c_ulong(), C.c_ulong()
            data = C.POINTER(C.c_ubyte)()
            x.XGetWindowProperty(display, window, atom, 0, 1, False, 6, C.byref(actual), C.byref(form), C.byref(items), C.byref(remaining), C.byref(data))
            value = C.cast(data, C.POINTER(C.c_ulong))[0] if data and items.value and form.value == 32 else 0
            if data:
                x.XFree(data)
            if value == pid and title(window).startswith('Orbiter | '):
                return window

    def key(window, name, down, state=0):
        code = x.XKeysymToKeycode(display, x.XStringToKeysym(name.encode()))
        require(code, 'Unknown key: ' + name)
        event = Event()
        timestamp = (time.monotonic_ns() // 1000000) & 0xffffffff
        event.key = KeyEvent(2 if down else 3, 0, True, display, window, root, 0, timestamp, 1, 1, 1, 1, state, code, True)
        require(x.XSendEvent(display, window, False, 1 if down else 2, C.byref(event)), 'Cannot send owned-window input')
        x.XFlush(display)

    def tap(window, name, modifier=None):
        scans = dict(space=57, F1=59, F5=63, F8=66, s=31, Control_L=29, Escape=1)
        def input_state():
            path = session / 'input-state.csv'
            lines = path.read_text().splitlines() if path.exists() else []
            if lines:
                fields = lines[-1].split(',')
                if len(fields) == 7 and fields[0].isdigit():
                    return int(fields[0]), bytes.fromhex(fields[1])
        def deliver(key_name, down, state=0):
            before = input_state() if record.get('observed') else None
            key(window, key_name, down, state)
            if before and key_name in scans and key_name != 'Escape':
                wait(lambda: (now := input_state()) and now[0] > before[0] and
                     bool(now[1][scans[key_name]]) == down,
                     'Actual input did not acknowledge key edge: ' + key_name)
            else:
                time.sleep(.1)
        if modifier:
            deliver(modifier, True)
        state = 4 if modifier == 'Control_L' else 0
        deliver(name, True, state)
        deliver(name, False, state)
        if modifier:
            deliver(modifier, False)
        time.sleep(.15)

    try:
        window = wait(owned, 'Walkthrough window did not appear', timeout=60)
        if args.exercise or args.resize:
            wait(lambda: 'PAUSED' in title(window), 'Walkthrough did not start paused', timeout=30)
        x.XRaiseWindow(display, window)
        x.XSetInputFocus(display, window, 1, 0)
        x.XFlush(display)
        time.sleep(1)
        (session / 'desktop-loaded-maps.txt').write_text(Path(f'/proc/{pid}/maps').read_text())
        capture(x, display, window, session / 'desktop-start.png')
        report = dict(status='visible-and-paused' if 'PAUSED' in title(window) else 'visible-and-running',
                      pid=pid, window=window, title=title(window), screenshot=str(session / 'desktop-start.png'))
        if args.resize:
            require(record.get('observed'), 'Resize check requires --observe at launch')
            x.XResizeWindow.argtypes = [C.c_void_p, C.c_ulong, C.c_uint, C.c_uint]
            x.XWarpPointer.argtypes = [C.c_void_p, C.c_ulong, C.c_ulong, C.c_int, C.c_int, C.c_uint, C.c_uint, C.c_int, C.c_int]
            def read_json(name):
                try:
                    return json.loads((session / name).read_text())
                except (OSError, ValueError):
                    return {}
            def rows(name):
                path = session / name
                text = path.read_text() if path.exists() else ''
                text = text[:text.rfind('\n') + 1]
                return [r for r in csv.DictReader(text.splitlines()) if r and all(v is not None for v in r.values())]
            def layout():
                data = rows('panel-layout.csv')
                return data[-1] if data else {}
            def camera():
                data = rows('cockpit-camera.csv')
                return data[-1] if data else {}
            if not layout():
                # The original read-only cockpit observer starts at the first
                # real pre-step; a scene opened paused has not reached it yet.
                tap(window, 'space')
                wait(lambda: 'RUNNING' in title(window), 'Cannot initialize live cockpit observation')
                wait(layout, 'Original panel was not observed after a real pre-step')
                tap(window, 'space')
                wait(lambda: 'PAUSED' in title(window), 'Cannot restore the initially paused view')
            base = wait(layout, 'No original panel layout observation')
            original_scale = float(base['scale'])
            local_points = [((px-float(base['x']))/original_scale,
                             (py-float(base['y']))/original_scale) for px, py in [(130, 430), (110, 430)]]
            sizes = []
            def resize(width, height, panel=False):
                x.XResizeWindow(display, window, width, height)
                x.XFlush(display)
                wait(lambda: read_json('native-window.json').get('framebuffer_width') == width and
                     read_json('native-window.json').get('framebuffer_height') == height,
                     'Actual client framebuffer did not resize')
                wait(lambda: read_json('cockpit-viewport.json') == dict(width=width, height=height),
                     'Original cockpit retained stale dimensions after resize')
                def gui_frames():
                    values = (session / 'ui-frames.csv').read_text().splitlines()
                    return int(values[-1]) if values and values[-1].isdigit() else 0
                before_frames = gui_frames()
                wait(lambda: gui_frames() >= before_frames + 2,
                     'Resized cockpit did not complete its GUI frames')
                if panel:
                    expected = original_scale * width / 1280
                    wait(lambda: layout() and abs(float(layout()['scale']) - expected) < 1e-10,
                         'Original DG panel did not scale to the resized window')
                    current = layout()
                    require(abs(float(current['x'])) < 1, 'Resized fit-to-width panel is not centered')
                    tap(window, 'space')
                    wait(lambda: 'RUNNING' in title(window), 'Cannot test resized panel clicks while running')
                    for point, mode in zip(local_points, ['LIN', 'ROT']):
                        px = round(float(current['x']) + point[0] * float(current['scale']))
                        py = round(float(current['y']) + point[1] * float(current['scale']))
                        x.XWarpPointer(display, 0, window, 0, 0, 0, 0, px, py)
                        x.XFlush(display)
                        time.sleep(.1)
                        def button(kind):
                            event = Event()
                            event.key = KeyEvent(kind, 0, True, display, window, root, 0, 0, px, py, 0, 0, 0 if kind == 4 else 256, 1, True)
                            x.XSendEvent(display, window, False, 4 if kind == 4 else 8, C.byref(event))
                            x.XFlush(display)
                        button(4)
                        try:
                            wait(lambda: 'RCS ' + mode + ' 0%' in title(window),
                                 'Resized visible RCS selector did not match its click target: ' + mode)
                        finally:
                            button(5)
                        time.sleep(.1)
                    tap(window, 'space')
                    wait(lambda: 'PAUSED' in title(window), 'Cannot restore pause after resized clicks')
                time.sleep(.2)
                mode = camera().get('mode', '?')
                filename = f'resized-{mode}-{width}x{height}.png'
                capture(x, display, window, session / filename)
                sizes.append(dict(width=width, height=height, mode=mode,
                                  layout=layout() if panel else None,
                                  screenshot=filename, aligned_rcs_clicks=panel))
                print('Passed resize', width, height, 'cockpit', mode, flush=True)
            for width, height in [(1920, 1080), (960, 540), (1280, 720)]:
                resize(width, height, panel=True)
            tap(window, 'F8')
            wait(lambda: camera().get('mode') == '3', 'Original virtual cockpit was not selected')
            orientation = {k: camera()[k] for k in ('phi', 'theta', 'aperture')}
            resize(1920, 1080)
            require({k: camera()[k] for k in orientation} == orientation,
                    'Resizing the virtual cockpit changed camera orientation/FOV')
            tap(window, 'F8')
            wait(lambda: camera().get('mode') == '1', 'Original glass cockpit was not selected')
            resize(960, 540)
            tap(window, 'F1')
            wait(lambda: camera().get('internal') == '0', 'Exterior view did not activate')
            x.XResizeWindow(display, window, 1280, 720)
            x.XFlush(display)
            wait(lambda: read_json('native-window.json').get('framebuffer_width') == 1280,
                 'Exterior framebuffer did not resize')
            tap(window, 'F1')
            wait(lambda: camera().get('internal') == '1', 'Cockpit did not reactivate')
            resize(1280, 720)
            time.sleep(2)
            timings = rows('frame-times.csv')[-60:]
            durations = [(int(b['present_end_ns']) - int(a['present_end_ns'])) / 1e6
                         for a, b in zip(timings, timings[1:])]
            require(len(durations) >= 30, 'Insufficient actual desktop frame times')
            report.update(status='passed-real-desktop-cockpit-resize', sizes=sizes,
                          renderer=read_json('renderer-info.json'),
                          measured_intervals=len(durations), median_frame_ms=statistics.median(durations),
                          p95_frame_ms=sorted(durations)[int(.95 * (len(durations)-1))],
                          virtual_cockpit_orientation_preserved=True,
                          exterior_resize_cockpit_reentry=True)
            require('Intel' in report['renderer'].get('renderer', '') and
                    'llvmpipe' not in report['renderer'].get('renderer', '').lower(),
                    'Resize walkthrough is not using the Intel GPU')
            tap(window, 'Escape')
        elif args.exercise:
            require(record.get('observed'), 'Full desktop input check requires --observe at launch')
            print('Desktop cockpit is rendered and paused', flush=True)
            tap(window, 'space')
            wait(lambda: 'PAUSED' not in title(window), 'Space did not resume the full stock scene')
            key(window, 'Alt_L', True)
            key(window, 'w', True, 8)
            wait(lambda: 'RCS ROT 100%' in title(window), 'Desktop Alt+W did not fire full RCS')
            key(window, 'w', False, 8)
            key(window, 'Alt_L', False)
            wait(lambda: 'RCS ROT 0%' in title(window), 'Desktop RCS did not stop on release')
            print('Desktop full thrust and key release passed', flush=True)
            tap(window, 'space')
            wait(lambda: 'PAUSED' in title(window), 'Space did not pause the full stock scene')
            tap(window, 'F8')
            capture(x, display, window, session / 'desktop-virtual-cockpit.png')
            save = HERE / 'saves/orbit-quicksave.scn'
            before = save.stat().st_mtime_ns if save.exists() else 0
            tap(window, 's', 'Control_L')
            wait(lambda: save.is_file() and save.stat().st_mtime_ns != before, 'Desktop Ctrl+S did not save')
            original = ships((HERE / 'assets/Scenarios/Delta-glider/DG Mk4 in orbit.scn').read_text())
            require(ships(save.read_text()) == original and len(original) == 8, 'Save omitted an original vessel')
            print('Desktop full eight-vessel save passed', flush=True)
            tap(window, 'F5')
            def replacement():
                current = owned()
                frames = session / 'session-2/ui-frames.csv'
                rows = frames.read_text().splitlines() if frames.exists() else []
                ready = len(rows) >= 10 and rows[-1].isdigit() and int(rows[-1]) >= 10
                return current if current and ready and 'PAUSED' in title(current) else None
            window = wait(replacement, 'A ready paused F5 replacement window did not appear', timeout=60)
            print('Desktop replacement world completed ten GUI frames', flush=True)
            time.sleep(2)
            x.XSetInputFocus(display, window, 1, 0)
            x.XFlush(display)
            capture(x, display, window, session / 'desktop-reloaded.png')
            (session / 'desktop-reloaded-maps.txt').write_text(Path(f'/proc/{pid}/maps').read_text())
            report.update(status='passed-desktop-full-stock-controls-save-reload',
                          original_vessels=original, save=str(save), keyboard_thrust_release=True,
                          pause_resume=True, cockpit_cycle=True, save_reload=True,
                          reloaded_window=window, reloaded_title=title(window))
            tap(window, 'Escape')
        elif args.close:
            tap(window, 'Escape')
        x.XSync(display, False)
        require(not errors, 'Unexpected desktop X11 errors: ' + str(errors))
        (session / 'desktop-probe.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
    finally:
        x.XCloseDisplay(display)


if __name__ == '__main__':
    main()
